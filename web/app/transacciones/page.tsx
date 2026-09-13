"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import TransactionList from "@/components/TransactionList";
import {
  fetchPurchases,
  formatMXN,
  purchaseToRow,
  type MerchantSummary,
  type Purchase,
} from "@/lib/api";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; purchases: Purchase[]; merchants: MerchantSummary[]; totalSpent: number };

const ALL = "Todas";

export default function TransaccionesPage() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [category, setCategory] = useState<string>(ALL);

  useEffect(() => {
    fetchPurchases()
      .then((body) =>
        setState({
          status: "success",
          purchases: body.data.purchases,
          merchants: body.data.merchants,
          totalSpent: Number(body.meta.total_spent ?? 0),
        }),
      )
      .catch((err: Error) => setState({ status: "error", message: err.message }));
  }, []);

  const categories = useMemo(() => {
    if (state.status !== "success") return [ALL];
    return [ALL, ...Array.from(new Set(state.purchases.map((p) => p.category)))];
  }, [state]);

  const visible = useMemo(() => {
    if (state.status !== "success") return null;
    const list = category === ALL ? state.purchases : state.purchases.filter((p) => p.category === category);
    return list.map(purchaseToRow);
  }, [state, category]);

  const visibleTotal = useMemo(() => {
    if (state.status !== "success") return 0;
    const list = category === ALL ? state.purchases : state.purchases.filter((p) => p.category === category);
    return list.reduce((acc, p) => acc + p.amount, 0);
  }, [state, category]);

  return (
    <AppShell>
      <div className="flex flex-1 flex-col gap-6">
        <div className="flex items-center gap-3 text-sm text-white/80">
          <Link href="/" className="hover:underline">
            Cuenta Checking
          </Link>
          <span>/</span>
          <span className="font-semibold text-white">Transacciones</span>
        </div>

        <div className="flex flex-1 flex-col gap-6 lg:flex-row lg:items-start">
          <div className="flex flex-1 flex-col gap-6">
            <div className="rounded-2xl bg-white p-6 shadow-card">
              <div className="flex items-start justify-between">
                <div>
                  <h1 className="text-sm font-semibold text-slate-500">Total gastado</h1>
                  <p className="mt-2 text-4xl font-bold text-brand-900">
                    {state.status === "success" ? formatMXN(visibleTotal) : "—"}
                  </p>
                  <p className="text-sm text-slate-500">
                    {state.status === "success"
                      ? `${visible?.length ?? 0} compras${category !== ALL ? ` en ${category}` : ""}`
                      : "Cargando..."}
                  </p>
                </div>
              </div>

              {state.status === "success" && (
                <div className="mt-5 flex flex-wrap gap-2">
                  {categories.map((c) => {
                    const active = c === category;
                    return (
                      <button
                        key={c}
                        type="button"
                        onClick={() => setCategory(c)}
                        className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
                          active
                            ? "bg-brand-700 text-white"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        {c}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            <TransactionList
              title="Todas las transacciones"
              transactions={visible}
              error={state.status === "error" ? state.message : null}
              emptyMessage="No hay compras en esta categoría."
            />
          </div>

          <div className="flex w-full flex-col gap-6 lg:w-96 lg:shrink-0">
            <div className="rounded-2xl bg-white p-6 shadow-card">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-bold text-slate-900">Por comercio</h2>
              </div>

              {state.status === "loading" && <p className="mt-4 text-sm text-slate-400">Cargando...</p>}
              {state.status === "error" && (
                <p className="mt-4 text-sm text-red-600">No se pudieron cargar: {state.message}</p>
              )}

              {state.status === "success" && (
                <ul className="mt-4 space-y-4">
                  {state.merchants.map((m) => {
                    const pct = state.totalSpent > 0 ? (m.total_spent / state.totalSpent) * 100 : 0;
                    return (
                      <li key={m.merchant_id ?? m.name}>
                        <div className="flex items-center justify-between text-sm">
                          <div>
                            <p className="font-medium text-slate-800">{m.name}</p>
                            <p className="text-xs text-slate-400">
                              {m.category} · {m.purchase_count} {m.purchase_count === 1 ? "compra" : "compras"}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="font-medium text-slate-800">{formatMXN(m.total_spent)}</p>
                            <p className="text-xs text-slate-400">{pct.toFixed(0)}%</p>
                          </div>
                        </div>
                        <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                          <div className="h-full rounded-full bg-brand-400" style={{ width: `${pct}%` }} />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
