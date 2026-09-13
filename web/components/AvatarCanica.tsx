"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";

// Claves que regresa /insights/{customer_id} (ver app/schemas.py:SectionInsights).
// Cada widget del dashboard se marca con data-avatar-target="<key>" para que la
// canica sepa a dónde saltar y qué conclusión mostrar ahí. `general` no tiene
// widget: se muestra en la "casita" del sidebar (data-avatar-home), igual que
// cualquier insight cuya sección NO esté en la página actual.
type InsightKey =
  | "general"
  | "balance"
  | "transactions"
  | "spending"
  | "banking_features"
  | "savings"
  | "credit"
  | "loans"
  | "rewards";

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

const STOP_DURATION_MS = 5000;
const TELEPORT_OUT_MS = 260;
const MARBLE_SIZE = 26;
const BUBBLE_WIDTH = 224; // w-56
const BUBBLE_GAP = 8; // separación entre canica y bubble
const EDGE_MARGIN = 12; // el bubble nunca queda a menos de esto del borde de pantalla

type Phase = "idle" | "out" | "in";
type Stop = { kind: "home"; el: HTMLElement } | { kind: "widget"; el: HTMLElement; key: InsightKey };
type Pos = { x: number; y: number; stop: Stop };
type Bubble = { left: number; top: number; width: number };

export default function AvatarCanica() {
  const pathname = usePathname();
  const [insights, setInsights] = useState<Insights>(FALLBACK_INSIGHTS);
  const [stops, setStops] = useState<Stop[]>([]);
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
          next.push({ kind: "widget", el, key: el.dataset.avatarTarget as InsightKey });
        }
        setStops(next);
        return;
      }
      tries += 1;
      raf = requestAnimationFrame(scan);
    };
    raf = requestAnimationFrame(scan);

    return () => cancelAnimationFrame(raf);
  }, [pathname]);

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
    const next: Pos =
      stop.kind === "home"
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

  useEffect(() => {
    if (stops.length === 0) {
      setPos(null);
      return;
    }
    const index = stopIndex % stops.length;
    moveTo(index, pos !== null);

    const interval = window.setInterval(() => {
      const total = stopsRef.current.length;
      setStopIndex((i) => {
        const nextIndex = (i + 1) % total;
        // Al volver a la casita (o si la casita es la única parada) rota el mensaje.
        if (stopsRef.current[nextIndex]?.kind === "home") setHomeMsgIndex((m) => m + 1);
        return nextIndex;
      });
    }, STOP_DURATION_MS);

    const reposition = () => moveTo(stopIndex % stopsRef.current.length, false);
    window.addEventListener("scroll", reposition, true);
    window.addEventListener("resize", reposition);

    return () => {
      window.clearInterval(interval);
      window.removeEventListener("scroll", reposition, true);
      window.removeEventListener("resize", reposition);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stops, stopIndex]);

  const current = pos?.stop;
  let message = "Analizando...";
  if (current?.kind === "widget") {
    message = insights[current.key] || message;
  } else if (current?.kind === "home" && homeMessages.length > 0) {
    message = homeMessages[homeMsgIndex % homeMessages.length];
  }

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

    if (stop.kind === "home") {
      const rect = stop.el.getBoundingClientRect();
      const width = Math.min(BUBBLE_WIDTH, rect.width - 16);
      const left = Math.min(Math.max(x - width / 2, rect.left + 8), rect.right - 8 - width);
      setBubble({ left: left - x, top: half + BUBBLE_GAP, width });
      return;
    }

    const h = bubbleRef.current.offsetHeight;
    const width = BUBBLE_WIDTH;

    // Horizontal: borde derecho del bubble bajo la canica (crece a la izquierda).
    let left = x + half - width;
    if (left < EDGE_MARGIN) left = x - half; // voltea: crece a la derecha
    left = Math.min(Math.max(left, EDGE_MARGIN), vw - EDGE_MARGIN - width);

    // Vertical: abajo de la canica; si se sale por abajo, arriba de ella.
    let top = y + half + BUBBLE_GAP;
    if (top + h > vh - EDGE_MARGIN) top = y - half - BUBBLE_GAP - h;
    top = Math.min(Math.max(top, EDGE_MARGIN), vh - EDGE_MARGIN - h);

    setBubble({ left: left - x, top: top - y, width });
  }, [pos, message]);

  if (!pos) return null;

  return (
    <div
      className="pointer-events-none fixed left-0 top-0 z-[999]"
      style={{ transform: `translate(${pos.x}px, ${pos.y}px)` }}
    >
      {phase === "in" && (
        <span
          className="canica-ring absolute -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-brand-400"
          style={{ width: MARBLE_SIZE * 2, height: MARBLE_SIZE * 2, left: 0, top: 0 }}
        />
      )}

      <div
        className={`absolute -translate-x-1/2 -translate-y-1/2 rounded-full shadow-lg ${
          phase === "out" ? "canica-out" : phase === "in" ? "canica-in" : ""
        }`}
        style={{
          width: MARBLE_SIZE,
          height: MARBLE_SIZE,
          background:
            "radial-gradient(circle at 35% 30%, #a5c8ff 0%, #3b6fd6 55%, #1c3f8f 100%)",
        }}
        aria-hidden
      />

      {phase !== "out" && (
        <div
          ref={bubbleRef}
          className="absolute rounded-xl bg-slate-900 px-3 py-2 text-xs text-white shadow-xl"
          style={{
            left: bubble?.left ?? -BUBBLE_WIDTH / 2,
            top: bubble?.top ?? MARBLE_SIZE / 2 + BUBBLE_GAP,
            width: bubble?.width ?? BUBBLE_WIDTH,
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
