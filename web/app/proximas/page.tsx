"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import {
  badgeFor,
  fetchBills,
  fetchSummary,
  formatLongDate,
  formatMXN,
  initialOf,
  type BadgeColor,
  type Bill,
} from "@/lib/api";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; bills: Bill[]; monthlyTotal: number; balance: number | null };

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

const dueLabel = (days: number) => {
  if (days === 0) return "Hoy";
  if (days === 1) return "Mañana";
  return `En ${days} días`;
};

const dueClasses = (days: number) =>
  days <= 3
    ? "bg-red-100 text-red-700"
    : days <= 7
      ? "bg-amber-100 text-amber-700"
      : "bg-slate-100 text-slate-600";

export default function ProximasPage() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    Promise.all([fetchBills(), fetchSummary().catch(() => null)])
      .then(([bills, summary]) =>
        setState({
          status: "success",
          bills: bills.data,
          monthlyTotal: Number(bills.meta.monthly_total ?? 0),
          balance: summary?.data.balance ?? null,
        }),
      )
      .catch((err: Error) => setState({ status: "error", message: err.message }));
  }, []);

  const next7 =
    state.status === "success" ? state.bills.filter((b) => b.days_until <= 7).reduce((a, b) => a + b.amount, 0) : 0;

  return (
    <AppShell>
      <div className="flex flex-1 flex-col gap-6">
        <div className="flex items-center gap-3 text-sm text-white/80">
          <Link href="/" className="hover:underline">
            Cuenta Checking
          </Link>
          <span>/</span>
          <span className="font-semibold text-white">Próximas transacciones</span>
        </div>

        <div className="flex flex-1 flex-col gap-6 lg:flex-row lg:items-start">
          <div className="flex flex-1 flex-col gap-6">
            <div className="rounded-2xl bg-white p-6 shadow-card">
              <div className="flex items-center justify-between">
                <h1 className="text-base font-bold text-slate-900">Pagos programados</h1>
              </div>

              {state.status === "loading" && <p className="mt-4 text-sm text-slate-400">Cargando...</p>}
              {state.status === "error" && (
                <p className="mt-4 text-sm text-red-600">No se pudieron cargar: {state.message}</p>
              )}
              {state.status === "success" && state.bills.length === 0 && (
                <p className="mt-4 text-sm text-slate-500">No tienes pagos programados.</p>
              )}

              {state.status === "success" && state.bills.length > 0 && (
                <ul className="mt-4 divide-y divide-slate-100">
                  {state.bills.map((b) => (
                    <li key={b.id} className="flex items-center justify-between gap-3 py-4">
                      <div className="flex items-center gap-3">
                        <span
                          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-base font-bold text-white ${badgeClasses[badgeFor(b.category)]}`}
                        >
                          {initialOf(b.payee)}
                        </span>
                        <div>
                          <p className="text-sm font-medium text-slate-800">{b.payee}</p>
                          <p className="text-xs text-slate-400">
                            {b.category} · cada día {b.recurring_date} del mes
                          </p>
                        </div>
                      </div>

                      <div className="text-right">
                        <p className="text-sm font-medium text-slate-800">{formatMXN(-b.amount)}</p>
                        <p className="text-xs text-slate-400">{formatLongDate(b.next_payment_date)}</p>
                        <span
                          className={`mt-1 inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold ${dueClasses(b.days_until)}`}
                        >
                          {dueLabel(b.days_until)}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div className="flex w-full flex-col gap-6 lg:w-96 lg:shrink-0">
            <div className="rounded-2xl bg-white p-6 shadow-card">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-bold text-slate-900">Resumen</h2>
              </div>

              {state.status === "success" ? (
                <dl className="mt-4 space-y-4 text-sm">
                  <div className="flex items-center justify-between">
                    <dt className="text-slate-500">Total mensual comprometido</dt>
                    <dd className="font-semibold text-slate-900">{formatMXN(state.monthlyTotal)}</dd>
                  </div>
                  <div className="flex items-center justify-between">
                    <dt className="text-slate-500">Se cobra en los próximos 7 días</dt>
                    <dd className="font-semibold text-slate-900">{formatMXN(next7)}</dd>
                  </div>
                  {state.balance !== null && (
                    <div className="flex items-center justify-between border-t border-slate-100 pt-4">
                      <dt className="text-slate-500">Saldo después de todos los pagos</dt>
                      <dd
                        className={`font-semibold ${
                          state.balance - state.monthlyTotal < 0 ? "text-red-600" : "text-slate-900"
                        }`}
                      >
                        {formatMXN(state.balance - state.monthlyTotal)}
                      </dd>
                    </div>
                  )}
                </dl>
              ) : (
                <p className="mt-4 text-sm text-slate-400">
                  {state.status === "error" ? "Sin datos." : "Cargando..."}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
