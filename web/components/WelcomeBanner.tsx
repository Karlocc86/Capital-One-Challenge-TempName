"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createCajita, formatLongDate, formatMXN, type CajitaProposal, type WelcomeMessage } from "@/lib/api";

// Saludo del Agente Guía (GET /guide/welcome/{account_id}) al abrir el dashboard.
// El tono lo decide el backend según insolvencia próxima / quincena mañana con
// gasto esencial sin apartar / todo bien.
const TONE_STYLES: Record<WelcomeMessage["tone"], string> = {
  positive: "border-emerald-200 bg-emerald-50 text-emerald-900",
  neutral: "border-slate-200 bg-white text-slate-900",
  warning: "border-amber-200 bg-amber-50 text-amber-900",
};

type Props = {
  welcome: WelcomeMessage | null;
  error?: string | null;
};

export default function WelcomeBanner({ welcome, error }: Props) {
  const router = useRouter();
  const [creating, setCreating] = useState<string | null>(null);
  const [createdNames, setCreatedNames] = useState<Set<string>>(new Set());
  const [createError, setCreateError] = useState<string | null>(null);

  if (error || !welcome) return null;

  const handleCreate = async (proposal: CajitaProposal) => {
    setCreating(proposal.expense_name);
    setCreateError(null);
    try {
      await createCajita({
        name: proposal.expense_name,
        target_amount: proposal.suggested_amount,
        linked_expense_name: proposal.expense_name,
        reserve_date: proposal.reserve_by_date,
      });
      setCreatedNames((prev) => new Set(prev).add(proposal.expense_name));
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "No se pudo crear la cajita.");
    } finally {
      setCreating(null);
    }
  };

  return (
    <div className={`rounded-2xl border p-5 shadow-card ${TONE_STYLES[welcome.tone]}`}>
      <p className="text-sm font-medium">{welcome.greeting}</p>

      {createError && <p className="mt-2 text-xs text-red-600">{createError}</p>}

      {welcome.cajita_proposals.length > 0 && (
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
          {welcome.cajita_proposals.map((proposal) => {
            const done = createdNames.has(proposal.expense_name);
            return (
              <div
                key={proposal.expense_name}
                className="min-w-[220px] flex-1 rounded-xl bg-white/80 p-4 text-slate-900 shadow-sm"
              >
                <p className="text-sm font-semibold">{proposal.expense_name}</p>
                <p className="mt-1 text-xs text-slate-600">{proposal.reasoning}</p>
                <p className="mt-2 text-sm font-bold text-brand-900">{formatMXN(proposal.suggested_amount)}</p>
                <p className="text-[11px] text-slate-500">
                  Apartar antes del {formatLongDate(proposal.reserve_by_date)}
                </p>
                <button
                  type="button"
                  disabled={creating === proposal.expense_name}
                  onClick={() => (done ? router.push("/cajitas") : handleCreate(proposal))}
                  className="mt-3 w-full rounded-lg bg-brand-700 px-3 py-2 text-xs font-bold text-white transition-colors hover:bg-brand-800 disabled:opacity-60"
                >
                  {done ? "Ver en Cajitas" : creating === proposal.expense_name ? "Creando…" : proposal.cta_label}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
