"use client";

import { useEffect, useState } from "react";
import {
  confirmCajitaWithdrawal,
  fetchCajitas,
  formatLongDate,
  formatMXN,
  requestCajitaWithdrawal,
  type Cajita,
  type WithdrawalWarning,
} from "@/lib/api";

const STATUS_LABEL: Record<Cajita["status"], string> = {
  pending: "Pendiente",
  active: "Activa",
  released: "Liberada",
};

const STATUS_BADGE: Record<Cajita["status"], string> = {
  pending: "bg-slate-100 text-slate-600",
  active: "bg-emerald-100 text-emerald-700",
  released: "bg-slate-100 text-slate-400",
};

const SEVERITY_STYLES: Record<WithdrawalWarning["severity"], string> = {
  low: "border-sky-200 bg-sky-50 text-sky-900",
  medium: "border-amber-200 bg-amber-50 text-amber-900",
  high: "border-red-200 bg-red-50 text-red-900",
};

// Retiro anticipado en dos pasos: request-withdrawal decide si libera directo
// o regresa una advertencia; si hay advertencia el usuario confirma (doble
// confirmación si el backend lo marca) antes de llamar confirm-withdrawal.
type PendingWithdrawal = { cajita: Cajita; warning: WithdrawalWarning; doubleConfirmed: boolean };

export default function CajitasView() {
  const [cajitas, setCajitas] = useState<Cajita[] | null>(null);
  const [activeTotal, setActiveTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [requestingId, setRequestingId] = useState<number | null>(null);
  const [pending, setPending] = useState<PendingWithdrawal | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = () => {
    fetchCajitas()
      .then((body) => {
        setCajitas(body.data);
        setActiveTotal(body.meta.active_total);
        setError(null);
      })
      .catch((err: Error) => setError(err.message));
  };

  useEffect(load, []);

  const handleWithdraw = async (cajita: Cajita) => {
    setRequestingId(cajita.id);
    setActionError(null);
    try {
      const body = await requestCajitaWithdrawal(cajita.id);
      if (body.data.released) {
        setPending(null);
        load();
      } else if (body.data.warning) {
        setPending({ cajita, warning: body.data.warning, doubleConfirmed: false });
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "No se pudo procesar el retiro.");
    } finally {
      setRequestingId(null);
    }
  };

  const handleConfirmWithdraw = async () => {
    if (!pending) return;
    setActionError(null);
    try {
      await confirmCajitaWithdrawal(pending.cajita.id);
      setPending(null);
      load();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "No se pudo confirmar el retiro.");
    }
  };

  const active = cajitas?.filter((c) => c.status === "active") ?? [];
  const other = cajitas?.filter((c) => c.status !== "active") ?? [];
  const ordered = [...active, ...other];

  return (
    <div className="flex flex-1 flex-col gap-6">
      <div data-avatar-target="cajitas" className="rounded-2xl bg-white p-6 shadow-card">
        <div className="flex items-center justify-between">
          <h1 className="text-base font-bold text-slate-900">Cajitas</h1>
          {cajitas !== null && activeTotal > 0 && (
            <span className="text-xs font-semibold text-slate-500">
              {formatMXN(activeTotal)} apartados en total
            </span>
          )}
        </div>

        {error && <p className="mt-4 text-sm text-red-600">No se pudieron cargar tus cajitas: {error}</p>}

        {!error && cajitas === null && <p className="mt-4 text-sm text-slate-400">Cargando...</p>}

        {!error && cajitas !== null && cajitas.length === 0 && (
          <p className="mt-4 text-sm text-slate-500">
            Todavía no tienes cajitas. Cuando el Agente Guía te proponga apartar dinero para un gasto
            esencial, aparecerán aquí.
          </p>
        )}

        {actionError && <p className="mt-4 text-sm text-red-600">{actionError}</p>}

        {!error && cajitas !== null && cajitas.length > 0 && (
          <ul className="mt-4 divide-y divide-slate-100">
            {ordered.map((cajita) => (
              <li key={cajita.id} className="flex items-center justify-between gap-3 py-4">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-slate-800">{cajita.name}</p>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${STATUS_BADGE[cajita.status]}`}>
                      {STATUS_LABEL[cajita.status]}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    Para {cajita.linked_expense_name} · lista el {formatLongDate(cajita.reserve_date)}
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <p className="text-sm font-bold text-brand-900">{formatMXN(cajita.target_amount)}</p>
                  {cajita.status === "active" && (
                    <button
                      type="button"
                      disabled={requestingId === cajita.id}
                      onClick={() => handleWithdraw(cajita)}
                      className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-bold text-slate-600 transition-colors hover:bg-slate-100 disabled:opacity-60"
                    >
                      {requestingId === cajita.id ? "Revisando…" : "Retirar"}
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {pending && (
        <div className={`rounded-2xl border p-5 shadow-card ${SEVERITY_STYLES[pending.warning.severity]}`}>
          <p className="text-sm font-semibold">Vas a retirar de &quot;{pending.cajita.name}&quot; antes de tiempo</p>
          <p className="mt-2 text-sm">{pending.warning.message}</p>
          <p className="mt-2 text-xs">{pending.warning.reminder}</p>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            {pending.warning.requires_double_confirmation && !pending.doubleConfirmed ? (
              <button
                type="button"
                onClick={() => setPending({ ...pending, doubleConfirmed: true })}
                className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-bold text-white hover:bg-slate-800"
              >
                Entiendo, quiero continuar
              </button>
            ) : (
              <button
                type="button"
                onClick={handleConfirmWithdraw}
                className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-bold text-white hover:bg-slate-800"
              >
                Confirmar retiro
              </button>
            )}
            <button
              type="button"
              onClick={() => setPending(null)}
              className="rounded-lg px-4 py-2 text-xs font-bold text-slate-600 hover:underline"
            >
              Mejor no, seguir apartando
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
