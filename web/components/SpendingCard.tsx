import { spending } from "@/lib/mockData";

const currency = (value: number) =>
  value.toLocaleString("en-US", { style: "currency", currency: "USD" });

export default function SpendingCard() {
  const inPct = Math.min(100, (spending.moneyIn / spending.moneyInGoal) * 100);
  const outPct = Math.min(100, (spending.moneyOut / spending.moneyInGoal) * 100);

  return (
    <div className="rounded-2xl bg-white p-6 shadow-card">
      <h2 className="text-sm font-semibold text-slate-800">Gastos</h2>

      <div className="mt-4 space-y-4">
        <div>
          <p className="text-sm text-slate-600">
            Ingresos {currency(spending.moneyIn)} de {currency(spending.moneyInGoal)}
          </p>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-green-500" style={{ width: `${inPct}%` }} />
          </div>
        </div>

        <div>
          <p className="text-sm text-slate-600">Egresos {currency(spending.moneyOut)}</p>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-blue-500" style={{ width: `${outPct}%` }} />
          </div>
        </div>
      </div>
    </div>
  );
}
