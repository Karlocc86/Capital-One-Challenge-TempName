"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import CardMenu from "@/components/CardMenu";

type CreditCardAccount = {
  _id: string;
  nickname: string;
  balance: number;
  total_spent: number;
  purchase_count: number;
  account_number: string;
};

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; cards: CreditCardAccount[] };

const currency = (value: number) =>
  value.toLocaleString("en-US", { style: "currency", currency: "USD" });

export default function TarjetasDeCreditoPage() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const customerId = process.env.NEXT_PUBLIC_DEMO_CUSTOMER_ID;

    fetch(`${apiUrl}/credit-cards/${customerId}`)
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`Backend respondió ${res.status}`);
        }
        return res.json();
      })
      .then((body) => {
        setState({ status: "success", cards: body.data });
      })
      .catch((err: Error) => {
        setState({ status: "error", message: err.message });
      });
  }, []);

  return (
    <AppShell>
      <div className="flex flex-1 flex-col gap-6">
        <div className="rounded-2xl bg-white p-6 shadow-card">
          <div className="flex items-center justify-between">
            <h1 className="text-base font-bold text-slate-900">Tarjetas de Crédito</h1>
            <CardMenu />
          </div>

          {state.status === "loading" && (
            <p className="mt-4 text-sm text-slate-400">Cargando tarjetas...</p>
          )}

          {state.status === "error" && (
            <p className="mt-4 text-sm text-red-600">
              No se pudieron cargar tus tarjetas: {state.message}
            </p>
          )}

          {state.status === "success" && state.cards.length === 0 && (
            <p className="mt-4 text-sm text-slate-500">
              Todavía no tienes tarjetas de crédito.
            </p>
          )}

          {state.status === "success" && state.cards.length > 0 && (
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              {state.cards.map((card) => (
                <div key={card._id} className="rounded-xl border border-slate-100 p-4">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-500 text-base font-bold text-white">
                      T
                    </span>
                    <div>
                      <p className="text-sm font-medium text-slate-800">{card.nickname}</p>
                      <p className="text-xs text-slate-400">
                        •••• {card.account_number?.slice(-4)}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-sm">
                    <span className="text-slate-500">Saldo disponible</span>
                    <span className="font-medium text-slate-800">{currency(card.balance)}</span>
                  </div>

                  <div className="mt-2 flex items-center justify-between text-sm">
                    <span className="text-slate-500">Gasto total</span>
                    <span className="font-medium text-slate-800">
                      {currency(card.total_spent)} · {card.purchase_count} compras
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
