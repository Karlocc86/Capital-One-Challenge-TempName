/**
 * Único punto de contacto del frontend con el backend (FastAPI). Nunca se
 * llama a Nessie desde aquí: todo pasa por el backend (NEXT_PUBLIC_API_URL).
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

/** ¿Llega a fin de mes? Lo calcula el forecaster (app/forecaster.py), no el LLM. */
export type MonthEndAnalysis = {
  month_end_date: string;
  projected_balance: number;
  lowest_balance_until_month_end: number;
  reaches_month_end: boolean;
  monthly_income: number;
  monthly_outflow: number;
  monthly_deficit: number;
};

export type ForecastMetrics = {
  burn_rate_daily: number;
  insolvency_date: string | null;
  days_remaining: number | null;
  confidence: number | null;
  next_paycheck_date: string | null;
  paycheck_amount: number | null;
  lowest_balance: number | null;
  lowest_balance_date: string | null;
  month_end: MonthEndAnalysis | null;
  /** Saldo proyectado día a día (90 días) con los cargos/abonos puntuales de cada día. */
  projection: ProjectionPoint[];
};

export type RecommendationArea =
  | "paso_de_hoy"
  | "fin_de_mes"
  | "suscripciones"
  | "comida_chatarra"
  | "gastos_hormiga"
  | "vida_social"
  | "movimiento"
  | "salud_preventiva"
  | "ahorro"
  | "integral";

export type Recommendation = {
  area: RecommendationArea;
  title: string;
  description: string;
  /** Qué gana en salud, descanso, relaciones o tranquilidad (enfoque de bienestar integral). */
  wellbeing_benefit: string;
  estimated_impact: string;
  priority: number;
};

export const RECOMMENDATION_AREA_LABELS: Record<RecommendationArea, string> = {
  paso_de_hoy: "Tu paso de hoy",
  fin_de_mes: "Fin de mes",
  suscripciones: "Suscripciones",
  comida_chatarra: "Comida chatarra",
  gastos_hormiga: "Gastos hormiga",
  vida_social: "Vida social",
  movimiento: "Movimiento",
  salud_preventiva: "Salud preventiva",
  ahorro: "Ahorro",
  integral: "Integral",
};

export type RescuePlan = {
  summary: string;
  insolvency_warning: string;
  /** Una por área, ordenadas por prioridad (1 = más importante). */
  recommendations: Recommendation[];
};

export type Forecast = {
  account_id: string;
  forecast: ForecastMetrics;
  rescue_plan: RescuePlan;
};

// ---------- Cajitas (app/cajitas.py, app/schemas.py) ----------

export type CajitaProposal = {
  expense_name: string;
  suggested_amount: number;
  reserve_by_date: string;
  reasoning: string;
  cta_label: string;
};

/** Saludo del Agente Guía al abrir el dashboard (GET /guide/welcome/{account_id}). */
export type WelcomeMessage = {
  greeting: string;
  tone: "positive" | "neutral" | "warning";
  cajita_proposals: CajitaProposal[];
};

export type Cajita = {
  id: number;
  account_id: string;
  name: string;
  target_amount: number;
  linked_expense_name: string;
  reserve_date: string;
  status: "pending" | "active" | "released";
  was_early_withdrawal: boolean;
  days_early_at_withdrawal: number | null;
  created_at: string;
};

export type WithdrawalWarning = {
  message: string;
  days_early: number;
  severity: "low" | "medium" | "high";
  reminder: string;
  requires_double_confirmation: boolean;
};

export type WithdrawalResult = {
  released: boolean;
  warning: WithdrawalWarning | null;
  cajita: Cajita;
};

// ---------- Fetchers ----------

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Backend respondió ${res.status} en ${path}`);
  }
  return res.json() as Promise<T>;
}

async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
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

export const fetchWelcome = (accountId = DEMO_ACCOUNT_ID) =>
  getJson<Envelope<WelcomeMessage>>(`/guide/welcome/${accountId}`);

export const fetchCajitas = (accountId = DEMO_ACCOUNT_ID) =>
  getJson<Envelope<Cajita[], { count: number; active_total: number; currency: string }>>(
    `/cajitas/${accountId}`,
  );

export const createCajita = (input: {
  name: string;
  target_amount: number;
  linked_expense_name: string;
  reserve_date: string;
  accountId?: string;
}) =>
  postJson<Envelope<Cajita, { created: boolean; currency: string }>>("/cajitas", {
    account_id: input.accountId ?? DEMO_ACCOUNT_ID,
    name: input.name,
    target_amount: input.target_amount,
    linked_expense_name: input.linked_expense_name,
    reserve_date: input.reserve_date,
  });

export const requestCajitaWithdrawal = (cajitaId: number) =>
  postJson<Envelope<WithdrawalResult, { days_early: number; currency: string }>>(
    `/cajitas/${cajitaId}/request-withdrawal`,
  );

export const confirmCajitaWithdrawal = (cajitaId: number) =>
  postJson<Envelope<Cajita, { days_early: number; currency: string }>>(
    `/cajitas/${cajitaId}/confirm-withdrawal`,
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

export type BadgeColor = "emerald" | "rose" | "red" | "green" | "sky" | "amber" | "violet" | "indigo" | "slate";

/** Color del círculo por categoría (la categoría viene del merchant en Nessie). */
const CATEGORY_BADGES: Record<string, BadgeColor> = {
  Supermercado: "sky",
  "Comida y bebida": "rose",
  "Comida chatarra": "rose",
  "Transporte y combustible": "red",
  "Servicios y facturas": "emerald",
  Salud: "green",
  Ropa: "amber",
  Ingresos: "emerald",
  Vivienda: "violet",
  Suscripciones: "indigo",
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
