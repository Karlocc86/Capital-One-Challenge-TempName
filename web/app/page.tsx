import Sidebar from "@/components/Sidebar";
import BalanceCard from "@/components/BalanceCard";
import ForecastCard from "@/components/ForecastCard";

export default function Home() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />

      <main className="flex-1 p-6 sm:p-10">
        <div className="mx-auto max-w-xl">
          <BalanceCard />
          <ForecastCard />
        </div>
      </main>
    </div>
  );
}
