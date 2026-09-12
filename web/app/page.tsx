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

export default function Home() {
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
    <main className="min-h-screen flex items-center justify-center p-8">
      {state.status === "loading" && (
        <p className="text-lg text-gray-500">Cargando resumen...</p>
      )}

      {state.status === "error" && (
        <p className="text-lg text-red-600">
          No se pudo cargar el resumen: {state.message}
        </p>
      )}

      {state.status === "success" && (
        <div className="flex flex-col gap-2 text-center">
          <h1 className="text-sm uppercase tracking-wide text-gray-500">
            {state.summary.nickname}
          </h1>
          <p className="text-5xl font-bold">
            ${state.summary.balance.toLocaleString()}
          </p>
          <p className="text-gray-600">
            Gasto total: ${state.summary.total_spent.toLocaleString()} (
            {state.summary.purchase_count} compras)
          </p>
        </div>
      )}
    </main>
  );
}
