"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";

type Loan = {
  _id: string;
  type: string;
  status: string;
  amount: number;
  monthly_payment: number;
  credit_score: number;
  description: string;
};

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; loans: Loan[] };

const currency = (value: number) =>
  value.toLocaleString("en-US", { style: "currency", currency: "USD" });

const statusColor: Record<string, string> = {
  approved: "bg-emerald-100 text-emerald-700",
  pending: "bg-amber-100 text-amber-700",
  denied: "bg-red-100 text-red-700",
};

export default function PrestamosPage() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const customerId = process.env.NEXT_PUBLIC_DEMO_CUSTOMER_ID;

    fetch(`${apiUrl}/loans/${customerId}`)
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`Backend respondió ${res.status}`);
        }
        return res.json();
      })
      .then((body) => {
        setState({ status: "success", loans: body.data });
      })
      .catch((err: Error) => {
        setState({ status: "error", message: err.message });
      });
  }, []);

  return (
    <AppShell>
      <div className="flex flex-1 flex-col gap-6">
        <div className="rounded-2xl bg-white p-6 shadow-card" data-avatar-target="loans">
          <div className="flex items-center justify-between">
            <h1 className="text-base font-bold text-slate-900">Préstamos</h1>
          </div>

          {state.status === "loading" && (
            <p className="mt-4 text-sm text-slate-400">Cargando préstamos...</p>
          )}

          {state.status === "error" && (
            <p className="mt-4 text-sm text-red-600">
              No se pudieron cargar tus préstamos: {state.message}
            </p>
          )}

          {state.status === "success" && state.loans.length === 0 && (
            <p className="mt-4 text-sm text-slate-500">
              Todavía no tienes préstamos activos.
            </p>
          )}

          {state.status === "success" && state.loans.length > 0 && (
            <ul className="mt-4 divide-y divide-slate-100">
              {state.loans.map((loan) => (
                <li key={loan._id} className="flex items-center justify-between gap-3 py-4">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-violet-500 text-base font-bold text-white">
                      P
                    </span>
                    <div>
                      <p className="text-sm font-medium capitalize text-slate-800">
                        {loan.type} · {loan.description || "Préstamo"}
                      </p>
                      <span
                        className={`mt-1 inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold capitalize ${
                          statusColor[loan.status] ?? "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {loan.status}
                      </span>
                    </div>
                  </div>

                  <div className="text-right">
                    <p className="text-sm font-medium text-slate-800">{currency(loan.amount)}</p>
                    <p className="text-xs text-slate-400">{currency(loan.monthly_payment)}/mes</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </AppShell>
  );
}
