import { balanceSummary } from "@/lib/mockData";

const currency = (value: number) =>
  value.toLocaleString("en-US", { style: "currency", currency: "USD" });

export default function BalanceOverviewCard() {
  return (
    <div className="rounded-2xl bg-white p-6 shadow-card">
      <div className="flex items-start justify-between">
        <h2 className="text-sm font-semibold text-slate-500">Mi Balance</h2>
        <button type="button" className="text-slate-400 hover:text-slate-600">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="5" cy="12" r="1.5" />
            <circle cx="12" cy="12" r="1.5" />
            <circle cx="19" cy="12" r="1.5" />
          </svg>
        </button>
      </div>

      <p className="mt-2 text-4xl font-bold text-brand-900">{currency(balanceSummary.balance)}</p>
      <p className="text-sm text-slate-500">Saldo disponible</p>

      <div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-4 text-sm">
        <span className="text-slate-500">
          Cuenta {balanceSummary.accountNumberMasked} · Ruta {balanceSummary.routingNumberMasked}
        </span>
        <button type="button" className="font-semibold text-brand-700 hover:underline">
          Detalles de la cuenta &gt;
        </button>
      </div>
    </div>
  );
}
