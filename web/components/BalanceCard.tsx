"use client";

import { useEffect, useState } from "react";

type Summary = {
  account_id: string;
  nickname: string;
  balance: number;
  total_spent: number;
  purchase_count: number;
};

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; summary: Summary };

const currency = (value: number) =>
  value.toLocaleString("en-US", { style: "currency", currency: "USD" });

export default function BalanceCard() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const accountId = process.env.NEXT_PUBLIC_DEMO_ACCOUNT_ID;

    fetch(`${apiUrl}/summary/${accountId}`)
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`Backend respondió ${res.status}`);
        }
        return res.json();
      })
      .then((body) => {
        setState({ status: "success", summary: body.data });
      })
      .catch((err: Error) => {
        setState({ status: "error", message: err.message });
      });
  }, []);

  return (
    <div className="rounded-2xl bg-white p-6 shadow-card">
      <h2 className="text-sm font-semibold text-slate-500">Mi Balance</h2>

      {state.status === "loading" && (
        <p className="mt-4 text-sm text-slate-400">Cargando saldo...</p>
      )}

      {state.status === "error" && (
        <p className="mt-4 text-sm text-red-600">
          No se pudo cargar el saldo: {state.message}
        </p>
      )}

      {state.status === "success" && (
        <>
          <p className="mt-2 text-4xl font-bold text-brand-900">
            {currency(state.summary.balance)}
          </p>
          <p className="text-sm text-slate-500">Saldo disponible</p>

          <div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-4 text-sm">
            <span className="text-slate-500">{state.summary.nickname}</span>
            <span className="font-medium text-slate-700">
              {currency(state.summary.total_spent)} gastado ·{" "}
              {state.summary.purchase_count} compras
            </span>
          </div>
        </>
      )}
    </div>
  );
}
