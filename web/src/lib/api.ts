// Appels à l'API FastAPI (api/main.py) et types des réponses.

export interface Meta {
  min_date: string;
  max_date: string;
  default_start: string;
  default_end: string;
  states: string[];
}

export interface Filters {
  start: string;
  end: string;
  states: string[];
}

export interface PageHeader {
  period: { start: string; end: string; previous: { start: string; end: string } | null };
  states: string[];
  /** Nombre de commandes de la sélection ; 0 = aucune donnée, la page n'en dit pas plus. */
  orders: number;
}

export type PageName = "dashboard" | "sales" | "customers" | "products" | "geography" | "satisfaction" | "deliveries";

/** Données d'une page : en-tête commun + contenu propre à la page (``T``). */
export type PageData<T> = PageHeader & Partial<T>;

export class ApiError extends Error {}

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Réponse non JSON : on garde le code HTTP.
    }
    throw new ApiError(detail);
  }
  return response.json() as Promise<T>;
}

export const fetchMeta = (signal?: AbortSignal) => getJson<Meta>("/api/meta", signal);

export function fetchPage<T>(page: PageName, filters: Filters, signal?: AbortSignal) {
  const params = new URLSearchParams({ start: filters.start, end: filters.end });
  if (filters.states.length) params.set("states", filters.states.join(","));
  return getJson<PageData<T>>(`/api/pages/${page}?${params}`, signal);
}

// --- Contenu des pages ------------------------------------------------------

export interface Monthly { month: string }
type Compared<K> = { kpis: K; previous_kpis: K | null };

export interface StateRevenue { customer_state: string; revenue: number; orders: number; customers: number; share: number }

export interface DashboardKpis {
  revenue: number;
  orders: number;
  customers: number;
  average_review: number | null;
  reviews: number;
}
export interface DashboardData extends Compared<DashboardKpis> {
  monthly: (Monthly & { revenue: number; orders: number; customers: number })[];
  monthly_reviews: (Monthly & { review_score: number })[];
  by_state: StateRevenue[];
  categories: { category: string; revenue: number; share: number }[];
  statuses: { status: string; orders: number; share: number }[];
  delivery_histogram: { days: number; orders: number; label: string }[];
  median_delivery_days: number | null;
}

export interface SalesKpis {
  revenue: number;
  orders: number;
  average_basket: number | null;
  freight_share: number | null;
  credit_card_share: number | null;
  average_installments: number | null;
}
export interface SalesData extends Compared<SalesKpis> {
  monthly: (Monthly & { revenue: number; orders: number; customers: number })[];
  payments: { payment_type: string; label: string; orders: number; basket: number; share: number }[];
  installments: { group: string; orders: number; basket: number | null; share: number }[];
}

export interface CustomerKpis {
  customers: number;
  repeat_rate: number | null;
  orders_per_customer: number | null;
  revenue_per_customer: number | null;
  credit_card_share: number | null;
  average_installments: number | null;
}
export interface CustomersData extends Compared<CustomerKpis> {
  monthly: (Monthly & { customers: number; orders: number })[];
  loyalty: { group: string; customers: number; share: number }[];
  heatmap: { days: string[]; hours: number[]; values: number[][] };
}

export interface SellerKpis {
  active_sellers: number;
  median_revenue: number | null;
  top10_share: number | null;
  small_seller_share: number | null;
  categories: number;
  average_item_price: number | null;
}
export interface Seller {
  seller_id: string; seller_state: string; revenue: number; orders: number; items: number;
  average_price: number; review_score: number | null; late_rate: number | null;
}
export interface CategoryStats {
  category: string; revenue: number; orders: number; sellers: number; average_price: number;
  share: number; review_score: number | null; reviews: number; late_rate: number | null;
}
export interface ProductsData extends Compared<SellerKpis> {
  categories: CategoryStats[];
  category_threshold: number;
  average_review: number | null;
  concentration: { seller_share: number; revenue_share: number }[];
  top_sellers: Seller[];
  watched_sellers: Seller[];
  watched_count: number;
  watch_min_orders: number;
  small_seller_orders: number;
}

export interface City { city: string; revenue: number; customers: number; share: number; lat: number | null; lng: number | null }
export interface GeographyData {
  by_state: (StateRevenue & { delivery_days: number | null; late_rate: number | null; freight_value: number | null })[];
  by_seller_state: { seller_state: string; revenue: number; sellers: number; share: number }[];
  cities: City[];
}

export interface SatisfactionKpis {
  reviewed: number;
  response_rate: number | null;
  average_review: number | null;
  satisfied_share: number | null;
  dissatisfied_share: number | null;
  comment_rate: number | null;
  dissatisfied_comment_rate: number | null;
}
export interface ScoreGroup { review_score: number | null; dissatisfied_share: number | null; orders: number }
export interface SatisfactionData extends Compared<SatisfactionKpis> {
  monthly: (Monthly & { review_score: number; dissatisfied_share: number; reviewed: number })[];
  distribution: { stars: number; orders: number; share: number; label: string }[];
  by_delivery: (ScoreGroup & { group: string })[];
  by_items: (ScoreGroup & { group: string })[];
  categories: (ScoreGroup & { category: string })[];
  category_threshold: number;
}

export interface LogisticsKpis {
  delivered: number;
  average_delivery_days: number | null;
  median_delivery_days: number | null;
  late_rate: number | null;
  average_delay_when_late: number | null;
  median_margin_days: number | null;
  average_handling_days: number | null;
  freight_share: number | null;
}
export interface DeliveriesData extends Compared<LogisticsKpis> {
  monthly: (Monthly & { late_rate: number; delivery_days: number; delivered: number })[];
  stages: (Monthly & { approval: number; handling: number; transit: number })[];
  stage_labels: Record<"approval" | "handling" | "transit", string>;
  histogram: { days: number; orders: number; label: string }[];
  review_by_delay: { bucket: string; review_score: number | null; orders: number; low_scores: number | null }[];
  low_score_rates: { very_late: number | null; early: number | null };
  by_state: {
    customer_state: string; delivery_days: number; late_rate: number;
    freight_value: number; review_score: number | null; delivered: number;
  }[];
}
