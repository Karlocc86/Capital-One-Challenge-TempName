import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";
import BalanceOverviewCard from "@/components/BalanceOverviewCard";
import TransactionList from "@/components/TransactionList";
import BankingFeaturesCard from "@/components/BankingFeaturesCard";
import SpendingCard from "@/components/SpendingCard";
import { recentTransactions, upcomingTransactions } from "@/lib/mockData";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />

      <div className="flex flex-1">
        <Sidebar />

        <main className="flex flex-1 flex-col gap-6 p-4 sm:p-8 lg:flex-row lg:items-start">
          <div className="flex flex-1 flex-col gap-6 lg:max-w-2xl">
            <BalanceOverviewCard />
            <TransactionList title="Transacciones recientes" transactions={recentTransactions} />
          </div>

          <div className="flex w-full flex-col gap-6 lg:w-80 lg:shrink-0">
            <TransactionList
              title="Próximas transacciones"
              transactions={upcomingTransactions}
              showViewAll
            />
            <BankingFeaturesCard />
            <SpendingCard />
          </div>
        </main>
      </div>
    </div>
  );
}
