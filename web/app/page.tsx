import AppShell from "@/components/AppShell";
import BalanceOverviewCard from "@/components/BalanceOverviewCard";
import TransactionList from "@/components/TransactionList";
import BankingFeaturesCard from "@/components/BankingFeaturesCard";
import SpendingCard from "@/components/SpendingCard";
import { recentTransactions, upcomingTransactions } from "@/lib/mockData";

export default function Home() {
  return (
    <AppShell>
      <div className="flex flex-1 flex-col gap-6 lg:flex-row lg:items-stretch">
        <div className="flex flex-1 flex-col gap-6">
          <BalanceOverviewCard />
          <TransactionList title="Transacciones recientes" transactions={recentTransactions} />
        </div>

        <div className="flex w-full flex-col gap-6 lg:w-96 lg:shrink-0">
          <TransactionList
            title="Próximas transacciones"
            transactions={upcomingTransactions}
            showViewAll
          />
          <BankingFeaturesCard />
          <SpendingCard />
        </div>
      </div>
    </AppShell>
  );
}
