"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import CardMenu from "@/components/CardMenu";

type RewardEntry = {
  account_id: string;
  nickname: string;
  rewards: number;
};

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; entries: RewardEntry[] };

export default function RecompensasPage() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const customerId = process.env.NEXT_PUBLIC_DEMO_CUSTOMER_ID;

    fetch(`${apiUrl}/rewards/${customerId}`)
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`Backend respondió ${res.status}`);
        }
        return res.json();
      })
      .then((body) => {
        setState({ status: "success", entries: body.data });
      })
      .catch((err: Error) => {
        setState({ status: "error", message: err.message });
      });
  }, []);

  const totalRewards =
    state.status === "success" ? state.entries.reduce((sum, e) => sum + e.rewards, 0) : 0;

  return (
    <AppShell>
      <div className="flex flex-1 flex-col gap-6">
        <div className="rounded-2xl bg-white p-6 shadow-card" data-avatar-target="rewards">
          <div className="flex items-center justify-between">
            <h1 className="text-base font-bold text-slate-900">Recompensas</h1>
            <CardMenu />
          </div>

          {state.status === "loading" && (
            <p className="mt-4 text-sm text-slate-400">Cargando recompensas...</p>
          )}

          {state.status === "error" && (
            <p className="mt-4 text-sm text-red-600">
              No se pudieron cargar tus recompensas: {state.message}
            </p>
          )}

          {state.status === "success" && (
            <>
              <p className="mt-2 text-4xl font-bold text-brand-900">{totalRewards} pts</p>
              <p className="text-sm text-slate-500">Puntos acumulados en todas tus cuentas</p>

              {state.entries.length > 0 && (
                <ul className="mt-6 divide-y divide-slate-100 border-t border-slate-100">
                  {state.entries.map((entry) => (
                    <li
                      key={entry.account_id}
                      className="flex items-center justify-between gap-3 py-4"
                    >
                      <div className="flex items-center gap-3">
                        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-500 text-base font-bold text-white">
                          R
                        </span>
                        <p className="text-sm font-medium text-slate-800">{entry.nickname}</p>
                      </div>
                      <p className="text-sm font-medium text-slate-800">{entry.rewards} pts</p>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}
