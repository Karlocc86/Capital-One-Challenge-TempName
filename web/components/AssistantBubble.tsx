export default function AssistantBubble() {
  return (
    <button
      type="button"
      aria-label="Asistente"
      className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-brand-700 text-white shadow-card transition-all hover:scale-105 hover:bg-brand-600 active:scale-95"
    >
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.75}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M12 3a7 7 0 0 0-7 7c0 2.1.9 3.9 2.3 5.1L7 20l3.6-1.3c.45.1.92.15 1.4.15a7 7 0 0 0 0-14Z" />
        <circle cx="9.5" cy="10" r="0.9" fill="currentColor" stroke="none" />
        <circle cx="12" cy="10" r="0.9" fill="currentColor" stroke="none" />
        <circle cx="14.5" cy="10" r="0.9" fill="currentColor" stroke="none" />
      </svg>
    </button>
  );
}
