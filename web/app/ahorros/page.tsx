"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import CardMenu from "@/components/CardMenu";

type SavingsAccount = {
  _id: string;
  nickname: string;
  balance: number;
  rewards: number;
  account_number: string;
};

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; accounts: SavingsAccount[] };

const currency = (value: number) =>
  value.toLocaleString("en-US", { style: "currency", currency: "USD" });

export default function AhorrosPage() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const customerId = process.env.NEXT_PUBLIC_DEMO_CUSTOMER_ID;

    fetch(`${apiUrl}/savings/${customerId}`)
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`Backend respondió ${res.status}`);
        }
        return res.json();
      })
      .then((body) => {
        setState({ status: "success", accounts: body.data });
      })
      .catch((err: Error) => {
        setState({ status: "error", message: err.message });
      });
  }, []);

  return (
    <AppShell>
      <div className="flex flex-1 flex-col gap-6">
        <div className="rounded-2xl bg-white p-6 shadow-card" data-avatar-target="savings">
          <div className="flex items-center justify-between">
            <h1 className="text-base font-bold text-slate-900">Ahorros</h1>
            <CardMenu />
          </div>

          {state.status === "loading" && (
            <p className="mt-4 text-sm text-slate-400">Cargando cuentas de ahorro...</p>
          )}

          {state.status === "error" && (
            <p className="mt-4 text-sm text-red-600">
              No se pudieron cargar tus ahorros: {state.message}
            </p>
          )}

          {state.status === "success" && state.accounts.length === 0 && (
            <p className="mt-4 text-sm text-slate-500">
              Todavía no tienes cuentas de ahorro.
            </p>
          )}

          {state.status === "success" && state.accounts.length > 0 && (
            <ul className="mt-4 divide-y divide-slate-100">
              {state.accounts.map((account) => (
                <li key={account._id} className="flex items-center justify-between gap-3 py-4">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-base font-bold text-white">
                      A
                    </span>
                    <div>
                      <p className="text-sm font-medium text-slate-800">{account.nickname}</p>
                      <p className="text-xs text-slate-400">
                        Cuenta •••• {account.account_number?.slice(-4)}
                      </p>
                    </div>
                  </div>

                  <div className="text-right">
                    <p className="text-sm font-medium text-slate-800">{currency(account.balance)}</p>
                    <p className="text-xs text-slate-400">{account.rewards} pts recompensa</p>
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
