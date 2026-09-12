import Image from "next/image";

export default function Header() {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-100 bg-white px-4 sm:h-20 sm:px-8">
      <Image src="/logo.png" alt="Capital Autonomy" width={160} height={34} priority className="h-10 w-auto sm:h-12" />

      <div className="flex items-center gap-4 sm:gap-6">
        <button
          type="button"
          className="hidden items-center gap-2 text-sm font-medium text-brand-700 hover:text-brand-900 sm:flex"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5Z" />
          </svg>
          <span>¿Necesitas ayuda?</span>
        </button>

        <button type="button" className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-700 text-sm font-semibold text-white">
            LP
          </span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-400">
            <path d="m6 9 6 6 6-6" />
          </svg>
        </button>
      </div>
    </header>
  );
}
