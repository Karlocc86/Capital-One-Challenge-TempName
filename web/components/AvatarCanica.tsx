"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { fetchForecast, type Recommendation, type RecommendationArea } from "@/lib/api";

// Claves que regresa /insights/{customer_id} (ver app/schemas.py:SectionInsights).
// Cada widget del dashboard se marca con data-avatar-target="<key>" para que la
// canica sepa a dónde saltar y qué conclusión mostrar ahí. `general` no tiene
// widget: se muestra en la "casita" del sidebar (data-avatar-home), igual que
// cualquier insight cuya sección NO esté en la página actual.
type InsightKey =
  | "general"
  | "balance"
  | "transactions"
  | "upcoming"
  | "spending"
  | "banking_features"
  | "savings"
  | "credit"
  | "loans"
  | "rewards";

// Tour principal: las recomendaciones del plan de rescate (/forecast). Cada
// área se muestra encima de la tarjeta que le corresponde; si esa tarjeta no
// está en la página actual, se muestra en la casita.
const AREA_TARGET: Record<RecommendationArea, InsightKey | "home"> = {
  paso_de_hoy: "home",
  fin_de_mes: "balance",
  suscripciones: "upcoming",
  comida_chatarra: "transactions",
  gastos_hormiga: "transactions",
  vida_social: "transactions",
  movimiento: "transactions",
  salud_preventiva: "transactions",
  ahorro: "spending",
  integral: "home",
};
const RECOMMENDATION_MS = 15_000; // cada recomendación se muestra 15 s (o hasta que hagan click en la canica)
const REC_BUBBLE_WIDTH = 288; // w-72: las recomendaciones traen más texto

type Insights = Partial<Record<InsightKey, string>>;

const FALLBACK_INSIGHTS: Insights = {
  general: "Observando tus hábitos...",
  balance: "Analizando tu saldo...",
  transactions: "Revisando tus movimientos...",
  spending: "Calculando tu patrón de gasto...",
  banking_features: "Explorando tus productos...",
  savings: "Revisando tus ahorros...",
  credit: "Revisando tus tarjetas...",
  loans: "Revisando tus préstamos...",
  rewards: "Sumando tus recompensas...",
};

// Orden fijo en que se rotan los mensajes de la casita: primero el general,
// luego los de secciones que no están en esta página.
const HOME_KEY_ORDER: InsightKey[] = [
  "general",
  "balance",
  "transactions",
  "spending",
  "banking_features",
  "savings",
  "credit",
  "loans",
  "rewards",
];

const STOP_DURATION_MS = 12_000; // insights por sección (ahorros, tarjetas, préstamos, recompensas...)
const TELEPORT_OUT_MS = 260;
const MARBLE_SIZE = 26;
const BUBBLE_WIDTH = 224; // w-56
const BUBBLE_GAP = 8; // separación entre canica y bubble
const EDGE_MARGIN = 12; // el bubble nunca queda a menos de esto del borde de pantalla

type Phase = "idle" | "out" | "in";
type Stop =
  | { kind: "home"; el: HTMLElement }
  | { kind: "widget"; el: HTMLElement; key: InsightKey }
  | { kind: "rec"; el: HTMLElement; rec: Recommendation; atHome: boolean };
type Pos = { x: number; y: number; stop: Stop };
type Bubble = { left: number; top: number; width: number };

export default function AvatarCanica() {
  const pathname = usePathname();
  const [insights, setInsights] = useState<Insights>(FALLBACK_INSIGHTS);
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [domStops, setDomStops] = useState<Stop[]>([]);
  const [stopIndex, setStopIndex] = useState(0);
  const [homeMsgIndex, setHomeMsgIndex] = useState(0);
  const [phase, setPhase] = useState<Phase>("idle");
  const [pos, setPos] = useState<Pos | null>(null);
  const [bubble, setBubble] = useState<Bubble | null>(null);
  const bubbleRef = useRef<HTMLDivElement>(null);

  // 1. Trae los insights una sola vez (no se llama a Gemini de nuevo en cada
  // cambio de página) — si falla, se quedan los textos genéricos de arriba.
  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const customerId = process.env.NEXT_PUBLIC_DEMO_CUSTOMER_ID;
    if (!apiUrl || !customerId) return;

    fetch(`${apiUrl}/insights/${customerId}`)
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(String(res.status)))))
      .then((body) => setInsights({ ...FALLBACK_INSIGHTS, ...body.data }))
      .catch(() => {
        /* se queda con FALLBACK_INSIGHTS — la canica nunca se rompe en demo */
      });

    // Recomendaciones del plan de rescate (ya vienen ordenadas por prioridad).
    // Si /forecast falla, la canica sigue con el tour de insights de arriba.
    fetchForecast()
      .then((body) => setRecs(body.data.rescue_plan.recommendations))
      .catch(() => {
        /* sin recomendaciones: tour de insights */
      });
  }, []);

  // 2. Cada vez que cambia de página, redescubre la casita y los widgets
  // marcados en el DOM actual. El recorrido siempre es:
  // casita → widget 1 → ... → widget n → casita (siguiente mensaje) → ...
  useEffect(() => {
    setStopIndex(0);
    setHomeMsgIndex(0);
    setPhase("idle");

    let tries = 0;
    let raf = 0;
    const scan = () => {
      const home = document.querySelector<HTMLElement>("[data-avatar-home]");
      const widgets = Array.from(document.querySelectorAll<HTMLElement>("[data-avatar-target]"));
      if (widgets.length > 0 || home || tries > 20) {
        const next: Stop[] = [];
        if (home) next.push({ kind: "home", el: home });
        for (const el of widgets) {
          // El ancla es el rectángulo blanco real (la tarjeta), no el div
          // marcador: si el marcador envuelve a la tarjeta, sus medidas pueden
          // no coincidir (flex, márgenes) y la canica quedaría fuera de la esquina.
          const card = el.classList.contains("bg-white") ? el : el.querySelector<HTMLElement>(".bg-white") ?? el;
          next.push({ kind: "widget", el: card, key: el.dataset.avatarTarget as InsightKey });
        }
        setDomStops(next);
        return;
      }
      tries += 1;
      raf = requestAnimationFrame(scan);
    };
    raf = requestAnimationFrame(scan);

    return () => cancelAnimationFrame(raf);
  }, [pathname]);

  // Tour a recorrer: si hay recomendaciones, una parada por recomendación
  // (10 s cada una) sobre su tarjeta o en la casita; si no, el tour de
  // insights por widget (5 s cada uno).
  const home = domStops.find((s) => s.kind === "home");
  const widgetByKey = new Map(
    domStops.filter((s): s is Extract<Stop, { kind: "widget" }> => s.kind === "widget").map((s) => [s.key, s.el]),
  );
  const recStops: Stop[] = recs
    .map((rec): Stop | null => {
      const target = AREA_TARGET[rec.area];
      const el = target === "home" ? home?.el : widgetByKey.get(target) ?? home?.el;
      return el ? { kind: "rec", el, rec, atHome: el === home?.el } : null;
    })
    .filter((s): s is Stop => s !== null);
  // Los insights por sección (ahorros, tarjetas, préstamos, recompensas,
  // funciones bancarias...) SIEMPRE forman parte del tour — con el texto de
  // respaldo mientras el backend responde — salvo en los widgets que ya
  // cubre una recomendación en esta página (para no repetir la tarjeta).
  const coveredKeys = new Set(
    recStops
      .filter((s): s is Extract<Stop, { kind: "rec" }> => s.kind === "rec" && !s.atHome)
      .map((s) => AREA_TARGET[s.rec.area]),
  );
  const insightStops = domStops.filter((s) => s.kind === "widget" && !coveredKeys.has(s.key));
  const stops: Stop[] = recStops.length > 0 ? [...insightStops, ...recStops] : domStops;

  // Mensajes que van a la casita: el general + los de secciones que no tienen
  // widget en esta página (para que ningún insight de Gemini se pierda).
  const visibleKeys = new Set(stops.filter((s) => s.kind === "widget").map((s) => (s as { key: InsightKey }).key));
  const homeMessages = HOME_KEY_ORDER.filter((k) => !visibleKeys.has(k))
    .map((k) => insights[k])
    .filter((m): m is string => Boolean(m));

  // 3. Posiciona la canica: centrada en la casita, o en la esquina superior
  // derecha del widget. El bubble se acomoda después (paso 4) midiendo su
  // tamaño real para nunca salirse de la pantalla.
  const moveTo = (index: number, animate: boolean) => {
    const stop = stops[index];
    if (!stop) return;
    const rect = stop.el.getBoundingClientRect();
    const atHome = stop.kind === "home" || (stop.kind === "rec" && stop.atHome);
    const next: Pos = atHome
      ? { x: rect.left + rect.width / 2, y: rect.top + Math.min(rect.height * 0.3, 32), stop }
      : { x: rect.right, y: rect.top, stop };

    if (!animate) {
      setPos(next);
      setPhase("idle");
      return;
    }

    setPhase("out");
    window.setTimeout(() => {
      setPos(next);
      setPhase("in");
    }, TELEPORT_OUT_MS);
  };

  const stopsRef = useRef(stops);
  stopsRef.current = stops;

  // Pasa a la siguiente parada (la usan el temporizador y el click en la canica).
  const stopIndexRef = useRef(stopIndex);
  stopIndexRef.current = stopIndex;
  const advance = () => {
    const total = stopsRef.current.length;
    if (total === 0) return;
    const nextIndex = ((stopIndexRef.current % total) + 1) % total;
    // Al volver a la casita (o si la casita es la única parada) rota el mensaje.
    if (stopsRef.current[nextIndex]?.kind === "home") setHomeMsgIndex((m) => m + 1);
    setStopIndex(nextIndex);
  };
  const advanceRef = useRef(advance);
  advanceRef.current = advance;
  const phaseRef = useRef(phase);
  phaseRef.current = phase;

  useEffect(() => {
    if (stops.length === 0) {
      setPos(null);
      return;
    }
    const index = stopIndex % stops.length;
    moveTo(index, pos !== null);

    // Avanza sola cada `stopDuration`; un click en la canica llama a
    // `advance` de inmediato y, como cambia `stopIndex`, este efecto se
    // vuelve a montar y el temporizador arranca de cero para la siguiente.
    const stopDuration = stops[index]?.kind === "rec" ? RECOMMENDATION_MS : STOP_DURATION_MS;
    const interval = window.setInterval(() => advanceRef.current(), stopDuration);

    // Reposiciona sin animación cuando la esquina de la tarjeta se mueve. No
    // basta con scroll/resize de ventana: las tarjetas crecen cuando llegan
    // los datos ("Cargando..." → lista) y empujan a las de abajo, así que se
    // observa el tamaño de la tarjeta actual y del body. Se ignora mientras la
    // canica está "saliendo" para no cortar el teletransporte.
    let ticking = false;
    const reposition = () => {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(() => {
        ticking = false;
        if (phaseRef.current !== "out") moveTo(stopIndex % stopsRef.current.length, false);
      });
    };
    window.addEventListener("scroll", reposition, true);
    window.addEventListener("resize", reposition);
    const observer = new ResizeObserver(reposition);
    observer.observe(document.body);
    const currentEl = stopsRef.current[index]?.el;
    if (currentEl) observer.observe(currentEl);

    return () => {
      window.clearInterval(interval);
      window.removeEventListener("scroll", reposition, true);
      window.removeEventListener("resize", reposition);
      observer.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domStops, recs, stopIndex]);

  const current = pos?.stop;
  let message: React.ReactNode = "Analizando...";
  let messageKey = "analizando";
  if (current?.kind === "rec") {
    const { rec } = current;
    messageKey = `rec-${rec.area}`;
    message = (
      <>
        <p className="font-semibold">{rec.title}</p>
        <p className="mt-1 text-white/85">{rec.description}</p>
        <p className="mt-1 text-sky-200">{rec.wellbeing_benefit}</p>
        <p className="mt-1 text-[11px] font-semibold text-emerald-300">{rec.estimated_impact}</p>
      </>
    );
  } else if (current?.kind === "widget") {
    message = insights[current.key] || message;
    messageKey = `insight-${current.key}`;
  } else if (current?.kind === "home" && homeMessages.length > 0) {
    message = homeMessages[homeMsgIndex % homeMessages.length];
    messageKey = `home-${homeMsgIndex}`;
  }
  const bubbleWidth = current?.kind === "rec" ? REC_BUBBLE_WIDTH : BUBBLE_WIDTH;

  // 4. Acomoda el bubble con su tamaño real. En la casita va centrado bajo la
  // canica y dentro del sidebar. En un widget prefiere extenderse hacia la
  // izquierda (hacia adentro del widget) y hacia abajo; si por ese lado no
  // cabe en el viewport, se voltea al lado contrario en vez de recortarse.
  useLayoutEffect(() => {
    if (!pos || !bubbleRef.current) return;
    const { x, y, stop } = pos;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const half = MARBLE_SIZE / 2;

    if (stop.kind === "home" || (stop.kind === "rec" && stop.atHome)) {
      const rect = stop.el.getBoundingClientRect();
      const width = Math.min(bubbleWidth, rect.width - 16);
      const left = Math.min(Math.max(x - width / 2, rect.left + 8), rect.right - 8 - width);
      setBubble({ left: left - x, top: half + BUBBLE_GAP, width });
      return;
    }

    const h = bubbleRef.current.offsetHeight;
    const width = bubbleWidth;

    // Horizontal: borde derecho del bubble bajo la canica (crece a la izquierda).
    let left = x + half - width;
    if (left < EDGE_MARGIN) left = x - half; // voltea: crece a la derecha
    left = Math.min(Math.max(left, EDGE_MARGIN), vw - EDGE_MARGIN - width);

    // Vertical: abajo de la canica; si se sale por abajo, arriba de ella.
    let top = y + half + BUBBLE_GAP;
    if (top + h > vh - EDGE_MARGIN) top = y - half - BUBBLE_GAP - h;
    top = Math.min(Math.max(top, EDGE_MARGIN), vh - EDGE_MARGIN - h);

    setBubble({ left: left - x, top: top - y, width });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pos, messageKey]);

  if (!pos) return null;

  return (
    <div
      className="pointer-events-none fixed left-0 top-0 z-[999]"
      style={{ transform: `translate(${pos.x}px, ${pos.y}px)` }}
    >
      {/*
        El centrado (-translate-1/2) y la animación (scale) viven en elementos
        distintos a propósito: ambos usan `transform`, y si van en el mismo
        nodo la keyframe pisa al translate y la canica queda 13 px fuera de la
        esquina al terminar la animación (fill-mode: forwards).
      */}
      {phase === "in" && (
        <span
          className="absolute -translate-x-1/2 -translate-y-1/2"
          style={{ width: MARBLE_SIZE * 2, height: MARBLE_SIZE * 2, left: 0, top: 0 }}
        >
          <span className="canica-ring block h-full w-full rounded-full border-2 border-brand-400" />
        </span>
      )}

      {/* La canica sí recibe clicks (el resto del overlay no): click = siguiente recomendación. */}
      <button
        type="button"
        onClick={() => {
          if (phase !== "out") advance();
        }}
        className="pointer-events-auto absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer rounded-full border-0 bg-transparent p-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70"
        style={{ width: MARBLE_SIZE, height: MARBLE_SIZE, left: 0, top: 0 }}
        aria-label="Siguiente recomendación"
        title="Siguiente recomendación"
      >
        <span
          className={`block h-full w-full rounded-full shadow-lg ${
            phase === "out" ? "canica-out" : phase === "in" ? "canica-in" : ""
          }`}
          style={{
            background:
              "radial-gradient(circle at 35% 30%, #a5c8ff 0%, #3b6fd6 55%, #1c3f8f 100%)",
          }}
        />
      </button>

      {phase !== "out" && (
        <div
          ref={bubbleRef}
          className="absolute rounded-xl bg-slate-900 px-3 py-2 text-xs text-white shadow-xl"
          style={{
            left: bubble?.left ?? -bubbleWidth / 2,
            top: bubble?.top ?? MARBLE_SIZE / 2 + BUBBLE_GAP,
            width: bubble?.width ?? bubbleWidth,
            visibility: bubble ? "visible" : "hidden",
          }}
          role="status"
          aria-live="polite"
        >
          {message}
        </div>
      )}
    </div>
  );
}
