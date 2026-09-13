import Link from "next/link";
import { formatMXN, type BadgeColor, type TransactionRow } from "@/lib/api";

const badgeClasses: Record<BadgeColor, string> = {
  emerald: "bg-emerald-500",
  rose: "bg-rose-500",
  red: "bg-red-600",
  green: "bg-green-600",
  sky: "bg-sky-500",
  amber: "bg-amber-500",
  violet: "bg-violet-500",
  slate: "bg-slate-500",
};

type Props = {
  title: string;
  transactions: TransactionRow[] | null;
  error?: string | null;
  emptyMessage?: string;
  /** Ruta de la vista completa; si se omite no se muestra "Ver todo". */
  viewAllHref?: string;
};

export default function TransactionList({
  title,
  transactions,
  error,
  emptyMessage = "Sin movimientos.",
  viewAllHref,
}: Props) {
  return (
    <div className="rounded-2xl bg-white p-6 shadow-card">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-bold text-slate-900">{title}</h2>
      </div>

      {error && <p className="mt-4 text-sm text-red-600">No se pudieron cargar: {error}</p>}

      {!error && transactions === null && (
        <p className="mt-4 text-sm text-slate-400">Cargando...</p>
      )}

      {!error && transactions !== null && transactions.length === 0 && (
        <p className="mt-4 text-sm text-slate-500">{emptyMessage}</p>
      )}

      {!error && transactions !== null && transactions.length > 0 && (
        <ul className="mt-4 divide-y divide-slate-100">
          {transactions.map((tx) => (
            <li key={tx.id} className="flex items-center justify-between gap-3 py-3">
              <div className="flex items-center gap-3">
                <span
                  className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-base font-bold text-white ${badgeClasses[tx.badge]}`}
                >
                  {tx.initial}
                </span>
                <div>
                  <p className="text-sm font-medium text-slate-800">{tx.merchant}</p>
                  <p className="text-xs text-slate-400">{tx.category}</p>
                </div>
              </div>

              <div className="text-right">
                <p
                  className={`text-sm font-medium ${tx.amount > 0 ? "text-emerald-600" : "text-slate-800"}`}
                >
                  {formatMXN(tx.amount)}
                </p>
                <p className="text-xs text-slate-400">{tx.date}</p>
              </div>
            </li>
          ))}
        </ul>
      )}

      {viewAllHref && (
        <Link
          href={viewAllHref}
          className="mt-3 inline-block text-[11px] font-bold uppercase tracking-wide text-brand-700 hover:underline"
        >
          Ver todo &gt;
        </Link>
      )}
    </div>
  );
}
