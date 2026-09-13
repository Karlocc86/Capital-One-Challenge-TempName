import AppShell from "@/components/AppShell";

export default function CajitasPage() {
  return (
    <AppShell>
      <div className="flex flex-1 flex-col gap-6">
        <div className="rounded-2xl bg-white p-6 shadow-card">
          <h1 className="text-base font-bold text-slate-900">Cajitas</h1>

          <p className="mt-4 text-sm text-slate-500">Próximamente.</p>
        </div>
      </div>
    </AppShell>
  );
}
