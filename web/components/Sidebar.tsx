import CreditWiseCard from "@/components/CreditWiseCard";

type NavItem = {
  label: string;
  icon: React.ReactNode;
  active?: boolean;
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
    label: "Cuenta Checking... 0096",
    active: true,
    icon: (
      <svg {...iconProps}>
        <rect x="3" y="6" width="18" height="13" rx="2" />
        <path d="M3 10h18" />
        <path d="M7 15h4" />
      </svg>
    ),
  },
  {
    label: "Ahorros... 3886",
    icon: (
      <svg {...iconProps}>
        <circle cx="12" cy="12" r="9" />
        <path d="M9 12h6M12 9v6" />
      </svg>
    ),
  },
  {
    label: "Tarjetas de Crédito... 9794",
    icon: (
      <svg {...iconProps}>
        <rect x="2.5" y="5" width="19" height="14" rx="2.2" />
        <path d="M2.5 9.5h19" />
        <path d="M6 14.5h4" />
      </svg>
    ),
  },
  {
    label: "Préstamos... 2284",
    icon: (
      <svg {...iconProps}>
        <path d="M4 21V9l8-6 8 6v12" />
        <path d="M9 21v-6h6v6" />
      </svg>
    ),
  },
  {
    label: "Recompensas",
    icon: (
      <svg {...iconProps}>
        <path d="M12 2 3 7l9 5 9-5-9-5Z" />
        <path d="M3 12l9 5 9-5" />
      </svg>
    ),
  },
];

export default function Sidebar() {
  return (
    <aside className="hidden h-full w-64 shrink-0 flex-col bg-brand-sidebar text-white sm:flex">
      <div className="h-6" />

      <nav className="flex flex-col gap-1 overflow-y-auto px-3">
        {navItems.map((item) => (
          <button
            key={item.label}
            type="button"
            className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors ${
              item.active
                ? "bg-brand-400/40 font-semibold text-white"
                : "font-medium text-brand-50/80 hover:bg-brand-600 hover:text-white"
            }`}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="flex-1" />

      <CreditWiseCard />

      <div className="px-3 py-6">
        <button
          type="button"
          className="flex w-full items-center gap-3 rounded-lg border border-white/20 px-3 py-2.5 text-left text-sm font-medium text-white/90 transition-colors hover:bg-brand-600"
        >
          <svg {...iconProps}>
            <circle cx="12" cy="12" r="9" />
            <path d="M12 8v8M8 12h8" />
          </svg>
          <span>Abrir cuenta nueva</span>
        </button>
      </div>
    </aside>
  );
}
