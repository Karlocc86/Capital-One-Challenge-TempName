/**
 * Único punto de contacto del frontend con el backend (FastAPI). Nunca se
 * llama a Nessie desde aquí: todo pasa por http://localhost:8000.
 *
 * Todas las respuestas vienen envueltas en { data, meta }. Los montos llegan
 * positivos con `direction: "in" | "out"`, las fechas en ISO (YYYY-MM-DD) y
 * la moneda es MXN — el formateo se hace aquí, en el cliente.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const DEMO_ACCOUNT_ID = process.env.NEXT_PUBLIC_DEMO_ACCOUNT_ID ?? "";

// ---------- Tipos (espejo de app/main.py) ----------

export type Envelope<T, M = Record<string, unknown>> = { data: T; meta: M };

export type Summary = {
  account_id: string;
  nickname: string;
  /** Saldo disponible = opening_balance + total_deposited − total_spent (app/ledger.py). */
  balance: number;
  opening_balance: number;
  bills_charged: number;
  account_number_masked: string | null;
  total_spent: number;
  total_deposited: number;
  purchase_count: number;
  money_in: number;
  money_out: number;
  deposit_count: number;
  money_in_goal: number;
  bills_monthly_total: number;
};

export type Purchase = {
  id: string;
  direction: "out";
  amount: number;
  date: string;
  merchant_id: string | null;
  merchant: string;
  category: string;
  description: string | null;
  status: string;
};

export type MerchantSummary = {
  merchant_id: string | null;
  name: string;
  category: string;
  total_spent: number;
  purchase_count: number;
};

export type PurchasesResponse = {
  purchases: Purchase[];
  merchants: MerchantSummary[];
};

export type Merchant = {
  merchant_id: string;
  name: string;
  category: string;
  address: Record<string, string> | null;
};

export type Bill = {
  id: string;
  payee: string;
  nickname: string;
  amount: number;
  recurring_date: number;
  next_payment_date: string;
  days_until: number;
  category: string;
  status: string;
  direction: "out";
};

export type ProjectionPoint = { date: string; balance: number; events: string[] };

export type ForecastMetrics = {
  burn_rate_daily: number;
  insolvency_date: string | null;
  days_remaining: number | null;
  confidence: number | null;
  next_paycheck_date: string | null;
  paycheck_amount: number | null;
  lowest_balance: number | null;
  lowest_balance_date: string | null;
  /** Saldo proyectado día a día (90 días) con los cargos/abonos puntuales de cada día. */
  projection: ProjectionPoint[];
};

export type RescueAction = { description: string; estimated_impact: string };

export type RescuePlan = {
  summary: string;
  insolvency_warning: string;
  recommended_actions: RescueAction[];
};

export type Forecast = {
  account_id: string;
  forecast: ForecastMetrics;
  rescue_plan: RescuePlan;
};

// ---------- Fetchers ----------

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Backend respondió ${res.status} en ${path}`);
  }
  return res.json() as Promise<T>;
}

export const fetchSummary = (accountId = DEMO_ACCOUNT_ID) =>
  getJson<Envelope<Summary>>(`/summary/${accountId}`);

export const fetchPurchases = (accountId = DEMO_ACCOUNT_ID) =>
  getJson<Envelope<PurchasesResponse>>(`/purchases/${accountId}`);

export const fetchMerchants = () => getJson<Envelope<Merchant[]>>(`/merchants`);

export const fetchBills = (accountId = DEMO_ACCOUNT_ID) =>
  getJson<Envelope<Bill[]>>(`/bills/${accountId}`);

export const fetchForecast = (accountId = DEMO_ACCOUNT_ID, forceRefresh = false) =>
  getJson<Envelope<Forecast>>(
    `/forecast/${accountId}${forceRefresh ? "?force_refresh=true" : ""}`,
  );

// ---------- Formato (es-MX / MXN) ----------

export const formatMXN = (value: number) =>
  value.toLocaleString("es-MX", { style: "currency", currency: "MXN" });

/** "2026-09-12" -> "12 sep" (sin año, como en el diseño). */
export const formatShortDate = (iso: string) => {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d)
    .toLocaleDateString("es-MX", { day: "numeric", month: "short" })
    .replace(".", "");
};

/** "2026-09-25" -> "25 de septiembre de 2026". */
export const formatLongDate = (iso: string) => {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("es-MX", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
};

// ---------- Presentación de transacciones ----------

export type BadgeColor = "emerald" | "rose" | "red" | "green" | "sky" | "amber" | "violet" | "slate";

/** Color del círculo por categoría (la categoría viene del merchant en Nessie). */
const CATEGORY_BADGES: Record<string, BadgeColor> = {
  Supermercado: "sky",
  "Comida y bebida": "rose",
  "Transporte y combustible": "red",
  "Servicios y facturas": "emerald",
  Salud: "green",
  Ropa: "amber",
  Ingresos: "emerald",
  Vivienda: "violet",
  Deuda: "red",
};

export const badgeFor = (category: string): BadgeColor => CATEGORY_BADGES[category] ?? "slate";

export const initialOf = (name: string) => (name.trim()[0] ?? "?").toUpperCase();

/** Forma que consumen las listas del dashboard, independiente de si viene de purchases o bills. */
export type TransactionRow = {
  id: string;
  merchant: string;
  category: string;
  /** Negativo = egreso, positivo = ingreso (ya con signo, listo para mostrar). */
  amount: number;
  date: string;
  initial: string;
  badge: BadgeColor;
};

export const purchaseToRow = (p: Purchase): TransactionRow => ({
  id: p.id,
  merchant: p.merchant,
  category: p.category,
  amount: -p.amount,
  date: formatShortDate(p.date),
  initial: initialOf(p.merchant),
  badge: badgeFor(p.category),
});

export const billToRow = (b: Bill): TransactionRow => ({
  id: b.id,
  merchant: b.payee,
  category: b.category,
  amount: -b.amount,
  date: formatShortDate(b.next_payment_date),
  initial: initialOf(b.payee),
  badge: badgeFor(b.category),
});
