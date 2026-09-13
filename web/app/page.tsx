import AppShell from "@/components/AppShell";
import Dashboard from "@/components/Dashboard";

// Server component a propósito: la carga de datos vive en <Dashboard> (client).
// Tener la página raíz como client component confundía al manifest de RSC de
// Next en dev tras cada HMR ("Could not find the module page.tsx#default").
export default function Home() {
  return (
    <AppShell>
      <Dashboard />
    </AppShell>
  );
}
