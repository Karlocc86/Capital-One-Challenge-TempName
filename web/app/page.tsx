"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import BalanceOverviewCard from "@/components/BalanceOverviewCard";
import TransactionList from "@/components/TransactionList";
import BankingFeaturesCard from "@/components/BankingFeaturesCard";
import SpendingCard from "@/components/SpendingCard";
import {
  billToRow,
  fetchBills,
  fetchPurchases,
  fetchSummary,
  purchaseToRow,
  type Summary,
  type TransactionRow,
} from "@/lib/api";

// Vistas previas del dashboard; "Ver todo" lleva a la lista completa
// (/transacciones y /proximas).
const RECENT_LIMIT = 7;
const UPCOMING_LIMIT = 5;

type Loadable<T> = { data: T | null; error: string | null };

const loading = <T,>(): Loadable<T> => ({ data: null, error: null });

export default function Home() {
  const [summary, setSummary] = useState<Loadable<Summary>>(loading);
  const [recent, setRecent] = useState<Loadable<TransactionRow[]>>(loading);
  const [upcoming, setUpcoming] = useState<Loadable<TransactionRow[]>>(loading);

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
  }, []);

  return (
    <AppShell>
      <div className="flex flex-1 flex-col gap-6 lg:flex-row lg:items-stretch">
        <div className="flex flex-1 flex-col gap-6">
          <BalanceOverviewCard summary={summary.data} error={summary.error} />
          <TransactionList
            title="Transacciones recientes"
            transactions={recent.data}
            error={recent.error}
            emptyMessage="Todavía no hay compras registradas."
            viewAllHref="/transacciones"
          />
        </div>

        <div className="flex w-full flex-col gap-6 lg:w-96 lg:shrink-0">
          <TransactionList
            title="Próximas transacciones"
            transactions={upcoming.data}
            error={upcoming.error}
            emptyMessage="No tienes pagos programados."
            viewAllHref="/proximas"
          />
          <BankingFeaturesCard />
          <SpendingCard summary={summary.data} error={summary.error} />
        </div>
      </div>
    </AppShell>
  );
}
