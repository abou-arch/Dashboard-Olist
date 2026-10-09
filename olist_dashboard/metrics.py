"""Calcul des indicateurs à partir des tables ``orders`` et ``items``."""

from dataclasses import dataclass

import pandas as pd

from olist_dashboard.config import EXCLUDED_STATUSES


def filter_orders(
    orders: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    states: list[str] | None = None,
) -> pd.DataFrame:
    """Commandes passées entre ``start`` et ``end`` (jours inclus), pour les États choisis."""
    day = orders["purchase_date"].dt.normalize()
    mask = day.between(pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize())
    if states:
        mask &= orders["customer_state"].isin(states)
    return orders[mask]


def sold(df: pd.DataFrame) -> pd.DataFrame:
    """Retire les commandes annulées ou indisponibles (aucune vente réalisée)."""
    return df[~df["order_status"].isin(EXCLUDED_STATUSES)]


@dataclass(frozen=True)
class Kpis:
    revenue: float
    orders: int
    customers: int
    average_basket: float | None
    average_review: float | None
    late_rate: float | None
    average_delivery_days: float | None


def _mean(series: pd.Series) -> float | None:
    series = series.dropna()
    return float(series.mean()) if len(series) else None


def compute_kpis(orders: pd.DataFrame) -> Kpis:
    sales = sold(orders)
    n_orders = len(sales)
    revenue = float(sales["revenue"].sum())
    delivered = orders[orders["order_status"] == "delivered"]
    return Kpis(
        revenue=revenue,
        orders=n_orders,
        customers=int(sales["customer_unique_id"].nunique()),
        average_basket=revenue / n_orders if n_orders else None,
        average_review=_mean(orders["review_score"]),
        late_rate=_mean(delivered["is_late"].astype("float")),
        average_delivery_days=_mean(delivered["delivery_days"]),
    )


def previous_period(start: pd.Timestamp, end: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Période de même durée qui précède immédiatement [start, end]."""
    start, end = pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize()
    length = end - start + pd.Timedelta(days=1)
    return start - length, start - pd.Timedelta(days=1)


def monthly_sales(orders: pd.DataFrame) -> pd.DataFrame:
    """CA et nombre de commandes par mois d'achat."""
    sales = sold(orders)
    month = sales["purchase_date"].dt.to_period("M").dt.to_timestamp()
    out = sales.groupby(month).agg(revenue=("revenue", "sum"), orders=("order_id", "count"))
    out.index.name = "month"
    return out.reset_index()


def revenue_by_category(items: pd.DataFrame, top: int = 10) -> pd.DataFrame:
    """Les ``top`` catégories qui génèrent le plus de CA (prix + port), avec leur part du total."""
    sales = sold(items)
    revenue = (sales["price"] + sales["freight_value"]).groupby(sales["category"]).sum()
    out = revenue.rename("revenue").sort_values(ascending=False).to_frame()
    out["share"] = out["revenue"] / out["revenue"].sum()
    return out.head(top).rename_axis("category").reset_index()


def revenue_by_state(orders: pd.DataFrame, top: int = 10) -> pd.DataFrame:
    sales = sold(orders)
    out = sales.groupby("customer_state").agg(revenue=("revenue", "sum"), orders=("order_id", "count"))
    out["share"] = out["revenue"] / out["revenue"].sum()
    return out.sort_values("revenue", ascending=False).head(top).reset_index()
