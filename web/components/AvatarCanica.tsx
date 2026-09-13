"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";

// Claves que debe regresar /insights/{customer_id} (ver app/schemas.py:SectionInsights).
// Cada widget del dashboard se marca con data-avatar-target="<key>" para que la
// canica sepa a dónde saltar y qué conclusión mostrar ahí.
type InsightKey =
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
  balance: "Analizando tu saldo...",
  transactions: "Revisando tus movimientos...",
  spending: "Calculando tu patrón de gasto...",
  banking_features: "Explorando tus productos...",
  savings: "Revisando tus ahorros...",
  credit: "Revisando tus tarjetas...",
  loans: "Revisando tus préstamos...",
  rewards: "Sumando tus recompensas...",
};

const STOP_DURATION_MS = 5000;
const TELEPORT_OUT_MS = 260;
const MARBLE_SIZE = 26;
const BUBBLE_WIDTH = 224; // w-56
const EDGE_MARGIN = 12; // nunca queda a menos de esto del borde de pantalla

type Phase = "idle" | "out" | "in";
type Pos = { x: number; y: number; bubbleLeft: number };

export default function AvatarCanica() {
  const pathname = usePathname();
  const [insights, setInsights] = useState<Insights>(FALLBACK_INSIGHTS);
  const [targets, setTargets] = useState<HTMLElement[]>([]);
  const [stopIndex, setStopIndex] = useState(0);
  const [phase, setPhase] = useState<Phase>("idle");
  const [pos, setPos] = useState<Pos | null>(null);

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

  // 2. Cada vez que cambia de página, redescubre los widgets marcados con
  // data-avatar-target en el DOM actual (cada página tiene widgets distintos).
  useEffect(() => {
    setStopIndex(0);
    setPhase("idle");

    let tries = 0;
    let raf = 0;
    const scan = () => {
      const found = Array.from(
        document.querySelectorAll<HTMLElement>("[data-avatar-target]")
      );
      if (found.length > 0 || tries > 20) {
        setTargets(found);
        return;
      }
      tries += 1;
      raf = requestAnimationFrame(scan);
    };
    raf = requestAnimationFrame(scan);

    return () => cancelAnimationFrame(raf);
  }, [pathname]);

  // 3. Posiciona la canica en la esquina superior derecha del widget y agenda
  // el siguiente salto. El bubble de texto se ancla hacia el lado con más
  // espacio libre para nunca salirse de la pantalla (se "pega a la pared").
  const moveTo = (index: number, animate: boolean) => {
    const el = targets[index];
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const x = rect.right;
    const y = rect.top;

    // Por default el bubble se extiende hacia la izquierda del punto (hacia
    // adentro del widget, que es donde casi siempre hay espacio). Si no
    // alcanza ni así, se recorta contra el borde de la pantalla.
    const bubbleLeftGlobal = Math.min(
      Math.max(x - BUBBLE_WIDTH, EDGE_MARGIN),
      window.innerWidth - EDGE_MARGIN - BUBBLE_WIDTH
    );
    const next: Pos = { x, y, bubbleLeft: bubbleLeftGlobal - x };

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

  const targetsRef = useRef(targets);
  targetsRef.current = targets;

  useEffect(() => {
    if (targets.length === 0) {
      setPos(null);
      return;
    }
    moveTo(stopIndex % targets.length, pos !== null);

    const interval = window.setInterval(() => {
      setStopIndex((i) => (i + 1) % targetsRef.current.length);
    }, STOP_DURATION_MS);

    const reposition = () => moveTo(stopIndex % targetsRef.current.length, false);
    window.addEventListener("scroll", reposition, true);
    window.addEventListener("resize", reposition);

    return () => {
      window.clearInterval(interval);
      window.removeEventListener("scroll", reposition, true);
      window.removeEventListener("resize", reposition);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targets, stopIndex]);

  if (!pos) return null;

  const currentKey = targets[stopIndex % targets.length]?.dataset.avatarTarget as
    | InsightKey
    | undefined;
  const message = (currentKey && insights[currentKey]) || "Analizando...";

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
          className="absolute rounded-xl bg-slate-900 px-3 py-2 text-xs text-white shadow-xl"
          style={{ left: pos.bubbleLeft, top: MARBLE_SIZE / 2 + 8, width: BUBBLE_WIDTH }}
          role="status"
          aria-live="polite"
        >
          {message}
        </div>
      )}
    </div>
  );
}
