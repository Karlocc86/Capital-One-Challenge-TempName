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

type ForecastMetrics = {
  burn_rate_daily: number;
  insolvency_date: string | null;
  days_remaining: number | null;
  confidence: number | null;
};

type Action = {
  description: string;
  estimated_impact: string;
};

type RescuePlan = {
  summary: string;
  insolvency_warning: string;
  recommended_actions: Action[];
};

type Forecast = {
  account_id: string;
  forecast: ForecastMetrics;
  rescue_plan: RescuePlan;
};

type ForecastState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; data: Forecast };

export default function Home() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [forecastState, setForecastState] = useState<ForecastState>({
    status: "loading",
  });

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

    fetch(`${apiUrl}/forecast/${accountId}`)
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`Backend respondió ${res.status}`);
        }
        return res.json();
      })
      .then((body) => {
        setForecastState({ status: "success", data: body.data });
      })
      .catch((err: Error) => {
        setForecastState({ status: "error", message: err.message });
      });
  }, []);

  return (
    <main className="min-h-screen flex flex-col items-center gap-10 p-8">
      <div className="flex-1 flex items-center justify-center">
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
      </div>

      <div className="w-full max-w-xl">
        {forecastState.status === "loading" && (
          <p className="text-center text-gray-500">
            Generando plan de rescate...
          </p>
        )}

        {forecastState.status === "error" && (
          <p className="text-center text-red-600">
            No se pudo generar el forecast: {forecastState.message}
          </p>
        )}

        {forecastState.status === "success" && (
          <div className="flex flex-col gap-4 rounded-lg border border-gray-200 p-6">
            {forecastState.data.forecast.insolvency_date ? (
              <div className="text-center">
                <p className="text-3xl font-bold text-red-600">
                  {forecastState.data.forecast.days_remaining} días
                </p>
                <p className="text-gray-600">
                  Proyección de insolvencia:{" "}
                  {forecastState.data.forecast.insolvency_date}
                </p>
              </div>
            ) : (
              <p className="text-center text-green-600">
                No se proyecta insolvencia con la tendencia actual.
              </p>
            )}

            <p className="text-gray-700">
              {forecastState.data.rescue_plan.insolvency_warning}
            </p>

            <p className="text-gray-700">
              {forecastState.data.rescue_plan.summary}
            </p>

            <ul className="flex flex-col gap-2">
              {forecastState.data.rescue_plan.recommended_actions.map(
                (action, i) => (
                  <li
                    key={i}
                    className="flex justify-between gap-4 rounded bg-gray-50 p-3"
                  >
                    <span>{action.description}</span>
                    <span className="shrink-0 font-medium text-gray-600">
                      {action.estimated_impact}
                    </span>
                  </li>
                ),
              )}
            </ul>
          </div>
        )}
      </div>
    </main>
  );
}
