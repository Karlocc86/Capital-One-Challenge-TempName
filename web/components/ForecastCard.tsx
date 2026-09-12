"use client";

import { useEffect, useState } from "react";

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

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; data: Forecast };

export default function ForecastCard() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const accountId = process.env.NEXT_PUBLIC_DEMO_ACCOUNT_ID;

    fetch(`${apiUrl}/forecast/${accountId}`)
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`Backend respondió ${res.status}`);
        }
        return res.json();
      })
      .then((body) => {
        setState({ status: "success", data: body.data });
      })
      .catch((err: Error) => {
        setState({ status: "error", message: err.message });
      });
  }, []);

  return (
    <div className="mt-6 rounded-2xl bg-white p-6 shadow-card">
      <h2 className="text-sm font-semibold text-slate-500">
        Plan de Rescate
      </h2>

      {state.status === "loading" && (
        <p className="mt-4 text-sm text-slate-400">
          Generando plan de rescate...
        </p>
      )}

      {state.status === "error" && (
        <p className="mt-4 text-sm text-red-600">
          No se pudo generar el forecast: {state.message}
        </p>
      )}

      {state.status === "success" && (
        <div className="mt-4 flex flex-col gap-4">
          {state.data.forecast.insolvency_date ? (
            <div className="text-center">
              <p className="text-3xl font-bold text-red-600">
                {state.data.forecast.days_remaining} días
              </p>
              <p className="text-sm text-slate-500">
                Proyección de insolvencia: {state.data.forecast.insolvency_date}
              </p>
            </div>
          ) : (
            <p className="text-center text-sm font-medium text-emerald-600">
              No se proyecta insolvencia con la tendencia actual.
            </p>
          )}

          <p className="text-sm text-slate-700">
            {state.data.rescue_plan.insolvency_warning}
          </p>

          <p className="text-sm text-slate-700">
            {state.data.rescue_plan.summary}
          </p>

          <ul className="flex flex-col gap-2">
            {state.data.rescue_plan.recommended_actions.map((action, i) => (
              <li
                key={i}
                className="flex items-center justify-between gap-4 rounded-lg bg-slate-50 p-3 text-sm"
              >
                <span className="text-slate-700">{action.description}</span>
                <span className="shrink-0 font-medium text-brand-700">
                  {action.estimated_impact}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
