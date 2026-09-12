import CardMenu from "@/components/CardMenu";
import { spending } from "@/lib/mockData";

const currency = (value: number) =>
  value.toLocaleString("en-US", { style: "currency", currency: "USD" });

export default function SpendingCard() {
  const inPct = Math.min(100, (spending.moneyIn / spending.moneyInGoal) * 100);
  const outPct = Math.min(100, (spending.moneyOut / spending.moneyInGoal) * 100);

  return (
    <div className="rounded-2xl bg-white p-6 shadow-card">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-bold text-slate-900">Gastos</h2>
        <CardMenu />
      </div>

      <div className="mt-4 space-y-4">
        <div>
          <p className="text-sm text-slate-600">
            Ingresos <span className="font-semibold text-slate-900">{currency(spending.moneyIn)}</span> de{" "}
            {currency(spending.moneyInGoal)}
          </p>
          <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-green-500" style={{ width: `${inPct}%` }} />
          </div>
        </div>

        <div>
          <p className="text-sm text-slate-600">
            Egresos <span className="font-semibold text-slate-900">{currency(spending.moneyOut)}</span>
          </p>
          <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-blue-500" style={{ width: `${outPct}%` }} />
          </div>
        </div>
      </div>
    </div>
  );
}
