"use client";

import { useEffect, useState } from "react";
import BalanceOverviewCard from "@/components/BalanceOverviewCard";
import TransactionList from "@/components/TransactionList";
import BankingFeaturesCard from "@/components/BankingFeaturesCard";
import SpendingCard from "@/components/SpendingCard";
import WelcomeBanner from "@/components/WelcomeBanner";
import {
  billToRow,
  fetchBills,
  fetchCajitas,
  fetchPurchases,
  fetchSummary,
  fetchWelcome,
  purchaseToRow,
  type Summary,
  type TransactionRow,
  type WelcomeMessage,
} from "@/lib/api";

// Vistas previas del dashboard; "Ver todo" lleva a la lista completa
// (/transacciones y /proximas).
const RECENT_LIMIT = 7;
const UPCOMING_LIMIT = 5;

type Loadable<T> = { data: T | null; error: string | null };

const loading = <T,>(): Loadable<T> => ({ data: null, error: null });

export default function Dashboard() {
  const [summary, setSummary] = useState<Loadable<Summary>>(loading);
  const [recent, setRecent] = useState<Loadable<TransactionRow[]>>(loading);
  const [upcoming, setUpcoming] = useState<Loadable<TransactionRow[]>>(loading);
  const [welcome, setWelcome] = useState<Loadable<WelcomeMessage>>(loading);
  const [activeCajitasTotal, setActiveCajitasTotal] = useState(0);

  useEffect(() => {
    // Cada tarjeta carga y falla por separado: si /bills truena, el saldo y
    // las compras se siguen mostrando.
    fetchSummary()
      .then((body) => setSummary({ data: body.data, error: null }))
      .catch((err: Error) => setSummary({ data: null, error: err.message }));

    fetchPurchases()
      .then((body) =>
        setRecent({ data: body.data.purchases.slice(0, RECENT_LIMIT).map(purchaseToRow), error: null }),
      )
      .catch((err: Error) => setRecent({ data: null, error: err.message }));

    fetchBills()
      // /bills ya viene ordenado por próxima fecha de cobro.
      .then((body) => setUpcoming({ data: body.data.slice(0, UPCOMING_LIMIT).map(billToRow), error: null }))
      .catch((err: Error) => setUpcoming({ data: null, error: err.message }));

    // Saludo del Agente Guía — una sola vez al montar, como pide NEXT_STEPS.
    fetchWelcome()
      .then((body) => setWelcome({ data: body.data, error: null }))
      .catch((err: Error) => setWelcome({ data: null, error: err.message }));

    // /summary no resta las Cajitas activas del saldo (decisión del backend);
    // se resta aquí para mostrar el disponible real.
    fetchCajitas()
      .then((body) => setActiveCajitasTotal(body.meta.active_total))
      .catch(() => {
        /* si falla, se muestra el saldo tal cual viene de /summary */
      });
  }, []);

  return (
    <div className="flex flex-1 flex-col gap-6">
      <WelcomeBanner welcome={welcome.data} error={welcome.error} />

      <div className="flex flex-1 flex-col gap-6 lg:flex-row lg:items-stretch">
        <div className="flex flex-1 flex-col gap-6">
          <div data-avatar-target="balance">
            <BalanceOverviewCard
              summary={summary.data}
              error={summary.error}
              reservedInCajitas={activeCajitasTotal}
            />
          </div>
          <div data-avatar-target="transactions">
            <TransactionList
              title="Transacciones recientes"
              transactions={recent.data}
              error={recent.error}
              emptyMessage="Todavía no hay compras registradas."
              viewAllHref="/transacciones"
            />
          </div>
        </div>

        <div className="flex w-full flex-col gap-6 lg:w-96 lg:shrink-0">
          <div data-avatar-target="upcoming">
            <TransactionList
              title="Próximas transacciones"
              transactions={upcoming.data}
              error={upcoming.error}
              emptyMessage="No tienes pagos programados."
              viewAllHref="/proximas"
            />
          </div>
          <div data-avatar-target="banking_features">
            <BankingFeaturesCard />
          </div>
          <div data-avatar-target="spending">
            <SpendingCard summary={summary.data} error={summary.error} />
          </div>
        </div>
      </div>
    </div>
  );
}
