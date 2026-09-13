import AvatarCanica from "@/components/AvatarCanica";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-100 p-3 sm:p-6">
      <div className="flex min-h-[calc(100vh-1.5rem)] flex-col overflow-hidden rounded-3xl shadow-xl sm:min-h-[calc(100vh-3rem)]">
        <Header />

        <div className="flex flex-1">
          <Sidebar />

          <main className="flex flex-1 flex-col gap-6 bg-[var(--background)] p-4 sm:p-8">
            {children}
          </main>
        </div>
      </div>

      <AvatarCanica />
    </div>
  );
}
