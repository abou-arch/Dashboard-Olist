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

export type PageName = "overview" | "logistics" | "satisfaction" | "sellers" | "customers";

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

export interface OverviewData {
  kpis: OverviewKpis;
  previous_kpis: OverviewKpis | null;
  monthly: (Monthly & { revenue: number; orders: number })[];
  categories: { category: string; revenue: number; share: number }[];
  by_state: { customer_state: string; revenue: number; orders: number; share: number }[];
}
export interface OverviewKpis {
  revenue: number;
  orders: number;
  customers: number;
  average_basket: number | null;
  average_review: number | null;
  late_rate: number | null;
  average_delivery_days: number | null;
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
export interface LogisticsData {
  kpis: LogisticsKpis;
  previous_kpis: LogisticsKpis | null;
  monthly: (Monthly & { late_rate: number; delivery_days: number; delivered: number })[];
  stages: (Monthly & { approval: number; handling: number; transit: number })[];
  stage_labels: Record<"approval" | "handling" | "transit", string>;
  review_by_delay: { bucket: string; review_score: number | null; orders: number; low_scores: number | null }[];
  low_score_rates: { very_late: number | null; early: number | null };
  by_state: {
    customer_state: string; delivery_days: number; late_rate: number;
    freight_value: number; review_score: number | null; delivered: number;
  }[];
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
export interface SatisfactionData {
  kpis: SatisfactionKpis;
  previous_kpis: SatisfactionKpis | null;
  monthly: (Monthly & { review_score: number; dissatisfied_share: number; reviewed: number })[];
  distribution: { stars: number; orders: number; share: number; label: string }[];
  by_delivery: (ScoreGroup & { group: string })[];
  by_items: (ScoreGroup & { group: string })[];
  categories: (ScoreGroup & { category: string })[];
  category_threshold: number;
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
export interface SellersData {
  kpis: SellerKpis;
  previous_kpis: SellerKpis | null;
  concentration: { seller_share: number; revenue_share: number }[];
  by_seller_state: { seller_state: string; revenue: number; sellers: number; share: number }[];
  categories: CategoryStats[];
  category_threshold: number;
  average_review: number | null;
  top_sellers: Seller[];
  watched_sellers: Seller[];
  watched_count: number;
  watch_min_orders: number;
  small_seller_orders: number;
}

export interface CustomerKpis {
  customers: number;
  repeat_rate: number | null;
  orders_per_customer: number | null;
  revenue_per_customer: number | null;
  credit_card_share: number | null;
  average_installments: number | null;
}
export interface City { city: string; revenue: number; customers: number; share: number; lat: number | null; lng: number | null }
export interface CustomersData {
  kpis: CustomerKpis;
  previous_kpis: CustomerKpis | null;
  loyalty: { group: string; customers: number; share: number }[];
  payments: { payment_type: string; label: string; orders: number; basket: number; share: number }[];
  installments: { group: string; orders: number; basket: number | null; share: number }[];
  heatmap: { days: string[]; hours: number[]; values: number[][] };
  cities: City[];
}
