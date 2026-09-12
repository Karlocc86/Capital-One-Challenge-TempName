const iconProps = {
  width: 22,
  height: 22,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

const features = [
  {
    label: "Enviar dinero",
    icon: (
      <svg {...iconProps}>
        <path d="M12 3v12" />
        <path d="m7 10 5 5 5-5" />
        <path d="M5 21h14" />
      </svg>
    ),
  },
  {
    label: "Transferir",
    icon: (
      <svg {...iconProps}>
        <path d="m17 2 4 4-4 4" />
        <path d="M3 11V9a4 4 0 0 1 4-4h14" />
        <path d="m7 22-4-4 4-4" />
        <path d="M21 13v2a4 4 0 0 1-4 4H3" />
      </svg>
    ),
  },
  {
    label: "Bloquear tarjeta",
    icon: (
      <svg {...iconProps}>
        <rect x="4" y="11" width="16" height="10" rx="2" />
        <path d="M8 11V7a4 4 0 0 1 8 0v4" />
      </svg>
    ),
  },
  {
    label: "Estados de cuenta",
    icon: (
      <svg {...iconProps}>
        <path d="M6 2h9l3 3v17H6z" />
        <path d="M9 13h6M9 17h6M9 9h3" />
      </svg>
    ),
  },
];

export default function BankingFeaturesCard() {
  return (
    <div className="rounded-2xl bg-white p-6 shadow-card">
      <h2 className="text-sm font-semibold text-slate-800">Funciones bancarias</h2>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {features.map((feature) => (
          <button
            key={feature.label}
            type="button"
            className="flex flex-col items-center gap-2 rounded-xl border border-slate-100 p-3 text-center text-xs font-medium text-brand-700 transition-colors hover:bg-brand-50"
          >
            {feature.icon}
            <span>{feature.label}</span>
          </button>
        ))}
      </div>

      <button type="button" className="mt-4 text-sm font-semibold text-brand-700 hover:underline">
        Ver todo &gt;
      </button>
    </div>
  );
}
