import AvatarCanica from "@/components/AvatarCanica";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";

/**
 * Layout a pantalla completa: header fijo arriba, sidebar fijo a la izquierda
 * y el lienzo (`bg-brand-canvas`) ocupando todo el resto del viewport — sin
 * márgenes, bordes redondeados ni sombra alrededor.
 */
export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-brand-canvas">
      <div className="sticky top-0 z-20">
        <Header />
      </div>

      <div className="flex flex-1">
        <Sidebar />

        <main className="flex min-w-0 flex-1 flex-col gap-6 bg-brand-canvas p-4 sm:p-8 lg:p-10">
          {children}
        </main>
      </div>

      <AvatarCanica />
    </div>
  );
}
