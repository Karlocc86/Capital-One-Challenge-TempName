import { formatMXN, type Summary } from "@/lib/api";

type Props = {
  summary: Summary | null;
  error?: string | null;
};

export default function BalanceOverviewCard({ summary, error }: Props) {
  return (
    <div className="flex flex-1 flex-col justify-between rounded-2xl bg-white p-6 shadow-card">
      <div>
        <div className="flex items-start justify-between">
          <h2 className="text-sm font-semibold text-slate-500">Mi Balance</h2>
        </div>

        {error ? (
          <p className="mt-2 text-sm text-red-600">No se pudo cargar el saldo: {error}</p>
        ) : summary === null ? (
          <p className="mt-2 text-4xl font-bold text-slate-300">—</p>
        ) : (
          <p className="mt-2 text-4xl font-bold text-brand-900">{formatMXN(summary.balance)}</p>
        )}
        <p className="text-sm text-slate-500">Saldo disponible</p>
      </div>

      <div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-4 text-sm">
        <span className="text-slate-500">
          {summary ? `${summary.nickname} ${summary.account_number_masked ?? ""}` : "Cuenta"}
        </span>
        <button type="button" className="text-[11px] font-bold uppercase tracking-wide text-brand-700 hover:underline">
          Detalles de la cuenta &gt;
        </button>
      </div>
    </div>
  );
}
