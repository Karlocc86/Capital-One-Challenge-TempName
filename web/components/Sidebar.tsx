"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type NavItem = {
  label: string;
  href: string;
  icon: React.ReactNode;
  chipColor: string;
};

const iconProps = {
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

const navItems: NavItem[] = [
  {
    label: "Cuenta Checking",
    href: "/",
    chipColor: "bg-brand-700",
    icon: (
      <svg {...iconProps}>
        <rect x="3" y="6" width="18" height="13" rx="2" />
        <path d="M3 10h18" />
        <path d="M7 15h4" />
      </svg>
    ),
  },
  {
    label: "Ahorros",
    href: "/ahorros",
    chipColor: "bg-emerald-500",
    icon: (
      <svg {...iconProps}>
        <circle cx="12" cy="12" r="9" />
        <path d="M9 12h6M12 9v6" />
      </svg>
    ),
  },
  {
    label: "Tarjetas de Crédito",
    href: "/tarjetas-de-credito",
    chipColor: "bg-slate-500",
    icon: (
      <svg {...iconProps}>
        <rect x="2.5" y="5" width="19" height="14" rx="2.2" />
        <path d="M2.5 9.5h19" />
        <path d="M6 14.5h4" />
      </svg>
    ),
  },
  {
    label: "Préstamos",
    href: "/prestamos",
    chipColor: "bg-violet-500",
    icon: (
      <svg {...iconProps}>
        <path d="M4 21V9l8-6 8 6v12" />
        <path d="M9 21v-6h6v6" />
      </svg>
    ),
  },
  {
    label: "Recompensas",
    href: "/recompensas",
    chipColor: "bg-amber-500",
    icon: (
      <svg {...iconProps}>
        <path d="M12 2 3 7l9 5 9-5-9-5Z" />
        <path d="M3 12l9 5 9-5" />
      </svg>
    ),
  },
  {
    label: "Cajitas",
    href: "/cajitas",
    chipColor: "bg-cyan-500",
    icon: (
      <svg {...iconProps}>
        <path d="M21 8 12 3 3 8l9 5 9-5Z" />
        <path d="M3 8v8l9 5 9-5V8" />
        <path d="M12 13v8" />
      </svg>
    ),
  },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    // La columna exterior estira el fondo oscuro a toda la altura de la página;
    // el aside interior queda fijo (sticky) bajo el header al hacer scroll.
    <div className="hidden w-64 shrink-0 bg-brand-sidebar sm:block">
    <aside className="sticky top-16 flex h-[calc(100vh-4rem)] w-64 flex-col bg-brand-sidebar text-white sm:top-20 sm:h-[calc(100vh-5rem)]">
      <div className="h-6" />

      <nav className="flex flex-col gap-1 overflow-y-auto px-3">
        {navItems.map((item) => {
          const active = pathname === item.href;

          return (
            <Link
              key={item.label}
              href={item.href}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition-colors ${
                active
                  ? "bg-white text-brand-700"
                  : "text-brand-50/80 hover:bg-brand-600 hover:text-white"
              }`}
            >
              <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-white ${item.chipColor}`}>
                {item.icon}
              </span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* "Casita" de la canica: el hueco libre bajo la navegación. Aquí muestra
          los insights que no pertenecen a ninguna sección visible en la página. */}
      <div className="min-h-[7.5rem] flex-1" data-avatar-home />
    </aside>
    </div>
  );
}
