import { creditWise } from "@/lib/mockData";

export default function CreditWiseCard() {
  const angle = (creditWise.score / creditWise.maxScore) * 360;

  return (
    <div className="mx-3 rounded-xl bg-brand-900/60 p-5 text-center">
      <p className="text-sm font-semibold text-white">CreditWise</p>

      <div
        className="relative mx-auto mt-4 h-28 w-28 rounded-full"
        style={{
          background: `conic-gradient(#4ade80 ${angle}deg, rgba(255,255,255,0.15) 0deg)`,
        }}
      >
        <div className="absolute inset-[8px] flex flex-col items-center justify-center rounded-full bg-brand-900">
          <span className="text-2xl font-bold text-white">{creditWise.score}</span>
          <span className="text-xs text-emerald-400">{creditWise.label}</span>
        </div>
      </div>

      <p className="mt-4 text-xs text-brand-50/70">Actualizado: {creditWise.updated}</p>
      <button type="button" className="mt-2 text-[11px] font-bold uppercase tracking-wide text-white hover:underline">
        Ver tu puntaje &gt;
      </button>
    </div>
  );
}
