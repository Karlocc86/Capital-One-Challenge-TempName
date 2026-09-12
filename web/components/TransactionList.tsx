import type { Transaction } from "@/lib/mockData";

const currency = (value: number) =>
  value.toLocaleString("en-US", { style: "currency", currency: "USD" });

type Props = {
  title: string;
  transactions: Transaction[];
  showViewAll?: boolean;
};

export default function TransactionList({ title, transactions, showViewAll }: Props) {
  return (
    <div className="rounded-2xl bg-white p-6 shadow-card">
      <h2 className="text-sm font-semibold text-slate-800">{title}</h2>

      <ul className="mt-4 divide-y divide-slate-100">
        {transactions.map((tx) => (
          <li key={tx.id} className="flex items-center justify-between gap-3 py-3">
            <div className="flex items-center gap-3">
              <span
                className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-semibold text-white ${tx.badgeColor}`}
              >
                {tx.initial}
              </span>
              <div>
                <p className="text-sm font-medium text-slate-800">{tx.merchant}</p>
                <p className="text-xs text-slate-400">{tx.category}</p>
              </div>
            </div>

            <div className="text-right">
              <p className="text-sm font-medium text-slate-800">{currency(tx.amount)}</p>
              <p className="text-xs text-slate-400">{tx.date}</p>
            </div>
          </li>
        ))}
      </ul>

      {showViewAll && (
        <button type="button" className="mt-3 text-sm font-semibold text-brand-700 hover:underline">
          Ver todo &gt;
        </button>
      )}
    </div>
  );
}
