"use client";

import { useEffect, useState } from "react";
import {
  fetchForecast,
  formatLongDate,
  formatMXN,
  RECOMMENDATION_AREA_LABELS,
  type Forecast,
  type RecommendationArea,
} from "@/lib/api";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; data: Forecast };

const areaClasses: Record<RecommendationArea, string> = {
  fin_de_mes: "bg-red-100 text-red-700",
  suscripciones: "bg-indigo-100 text-indigo-700",
  comida_chatarra: "bg-rose-100 text-rose-700",
  gastos_hormiga: "bg-amber-100 text-amber-700",
  ahorro: "bg-emerald-100 text-emerald-700",
  integral: "bg-brand-100 text-brand-700",
};

export default function ForecastCard() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    fetchForecast()
      .then((body) => setState({ status: "success", data: body.data }))
      .catch((err: Error) => setState({ status: "error", message: err.message }));
  }, []);

  return (
    <div className="rounded-2xl bg-white p-6 shadow-card">
      <h2 className="text-base font-bold text-slate-900">¿Llego a fin de mes?</h2>

      {state.status === "loading" && (
        <p className="mt-4 text-sm text-slate-400">Analizando tus movimientos...</p>
      )}

      {state.status === "error" && (
        <p className="mt-4 text-sm text-red-600">No se pudo generar el análisis: {state.message}</p>
      )}

      {state.status === "success" && (
        <div className="mt-4 flex flex-col gap-5">
          {state.data.forecast.insolvency_date ? (
            <div className="rounded-xl bg-red-50 p-4 text-center">
              <p className="text-3xl font-bold text-red-600">
                {state.data.forecast.days_remaining} días
              </p>
              <p className="text-sm text-slate-600">
                Te quedas sin saldo el {formatLongDate(state.data.forecast.insolvency_date)}
                {state.data.forecast.next_paycheck_date && (
                  <> · próxima nómina el {formatLongDate(state.data.forecast.next_paycheck_date)}</>
                )}
              </p>
            </div>
          ) : (
            <div className="rounded-xl bg-emerald-50 p-4 text-center">
              <p className="text-sm font-medium text-emerald-700">
                No se proyecta insolvencia con la tendencia actual.
              </p>
            </div>
          )}

          {state.data.forecast.month_end && (
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-slate-500">Ingresos / mes</dt>
                <dd className="font-semibold text-slate-900">
                  {formatMXN(state.data.forecast.month_end.monthly_income)}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Egresos / mes</dt>
                <dd className="font-semibold text-slate-900">
                  {formatMXN(state.data.forecast.month_end.monthly_outflow)}
                </dd>
              </div>
              <div className="col-span-2">
                <dt className="text-slate-500">Déficit a recortar</dt>
                <dd
                  className={`font-semibold ${
                    state.data.forecast.month_end.monthly_deficit > 0 ? "text-red-600" : "text-emerald-600"
                  }`}
                >
                  {formatMXN(state.data.forecast.month_end.monthly_deficit)} / mes
                </dd>
              </div>
            </dl>
          )}

          <p className="text-sm text-slate-700">{state.data.rescue_plan.insolvency_warning}</p>

          <ul className="flex flex-col gap-2">
            {state.data.rescue_plan.recommendations.map((rec) => (
              <li key={rec.area} className="rounded-xl bg-slate-50 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold ${areaClasses[rec.area]}`}
                    >
                      {RECOMMENDATION_AREA_LABELS[rec.area]}
                    </span>
                    <p className="mt-1 text-sm font-semibold text-slate-900">{rec.title}</p>
                    <p className="text-sm text-slate-600">{rec.description}</p>
                  </div>
                  <span className="shrink-0 text-right text-xs font-semibold text-brand-700">
                    {rec.estimated_impact}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
