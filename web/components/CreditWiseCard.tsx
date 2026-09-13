import { creditWise } from "@/lib/mockData";

/**
 * Puntaje CreditWise. Vive dentro de la tarjeta blanca de "Tarjetas de Crédito";
 * el score es estático (Nessie no expone historial crediticio).
 */
export default function CreditWiseCard() {
  const angle = (creditWise.score / creditWise.maxScore) * 360;

  return (
    <div className="flex flex-col items-center gap-4 rounded-xl border border-slate-100 p-4 sm:flex-row sm:gap-6">
      <div
        className="relative h-24 w-24 shrink-0 rounded-full"
        style={{
          background: `conic-gradient(#22c55e ${angle}deg, rgba(15,23,42,0.08) 0deg)`,
        }}
      >
        <div className="absolute inset-[7px] flex flex-col items-center justify-center rounded-full bg-white">
          <span className="text-2xl font-bold leading-none text-slate-900">{creditWise.score}</span>
          <span className="mt-1 text-xs font-medium text-emerald-600">{creditWise.label}</span>
        </div>
      </div>

      <div className="text-center sm:text-left">
        <p className="text-sm font-semibold text-slate-900">CreditWise</p>
        <p className="mt-1 text-sm text-slate-500">
          Tu puntaje de crédito · Actualizado: {creditWise.updated}
        </p>
        <button
          type="button"
          className="mt-2 text-xs font-bold uppercase tracking-wide text-brand-700 hover:underline"
        >
          Ver tu puntaje &gt;
        </button>
      </div>
    </div>
  );
}
