import { formatMXN, type Summary } from "@/lib/api";

type Props = {
  summary: Summary | null;
  error?: string | null;
};

/**
 * Ingresos: depósitos de nómina recibidos (money_in) contra el ingreso mensual
 * esperado del perfil (money_in_goal = DEMO_MONTHLY_INCOME en el backend).
 * Egresos: suma de todas las compras de la cuenta (total_spent).
 */
export default function SpendingCard({ summary, error }: Props) {
  const moneyIn = summary?.money_in ?? 0;
  const moneyInGoal = summary?.money_in_goal ?? 0;
  const moneyOut = summary?.total_spent ?? 0;

  const inPct = moneyInGoal > 0 ? Math.min(100, (moneyIn / moneyInGoal) * 100) : 0;
  const outPct = moneyInGoal > 0 ? Math.min(100, (moneyOut / moneyInGoal) * 100) : 0;

  return (
    <div className="rounded-2xl bg-white p-6 shadow-card">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-bold text-slate-900">Gastos</h2>
      </div>

      {error && <p className="mt-4 text-sm text-red-600">No se pudieron cargar: {error}</p>}

      {!error && summary === null && <p className="mt-4 text-sm text-slate-400">Cargando...</p>}

      {!error && summary !== null && (
        <div className="mt-4 space-y-4">
          <div>
            <p className="text-sm text-slate-600">
              Ingresos <span className="font-semibold text-slate-900">{formatMXN(moneyIn)}</span> de{" "}
              {formatMXN(moneyInGoal)}
            </p>
            <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-green-500" style={{ width: `${inPct}%` }} />
            </div>
          </div>

          <div>
            <p className="text-sm text-slate-600">
              Egresos <span className="font-semibold text-slate-900">{formatMXN(moneyOut)}</span>
              <span className="text-slate-400"> · {summary.purchase_count} compras</span>
            </p>
            <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-blue-500" style={{ width: `${outPct}%` }} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
