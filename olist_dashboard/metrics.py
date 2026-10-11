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


# --- Logistique --------------------------------------------------------------


def delivered(orders: pd.DataFrame) -> pd.DataFrame:
    return orders[(orders["order_status"] == "delivered") & orders["delay_days"].notna()]


@dataclass(frozen=True)
class LogisticsKpis:
    delivered: int
    average_delivery_days: float | None
    median_delivery_days: float | None
    late_rate: float | None
    average_delay_when_late: float | None
    median_margin_days: float | None
    average_handling_days: float | None
    freight_share: float | None


def _median(series: pd.Series) -> float | None:
    series = series.dropna()
    return float(series.median()) if len(series) else None


def compute_logistics_kpis(orders: pd.DataFrame) -> LogisticsKpis:
    done = delivered(orders)
    late = done[done["delay_days"] > 0]
    sales = sold(orders)
    revenue = sales["revenue"].sum()
    return LogisticsKpis(
        delivered=len(done),
        average_delivery_days=_mean(done["delivery_days"]),
        median_delivery_days=_median(done["delivery_days"]),
        late_rate=_mean((done["delay_days"] > 0).astype("float")),
        average_delay_when_late=_mean(late["delay_days"]),
        # Nombre de jours entre la livraison et la date estimée annoncée au client.
        median_margin_days=_median(-done["delay_days"]),
        average_handling_days=_mean(delivery_stages(done)["handling"]),
        freight_share=float(sales["freight_value"].sum() / revenue) if revenue else None,
    )


STAGES = {
    "approval": "Validation",
    "handling": "Préparation vendeur",
    "transit": "Transport",
}


def delivery_stages(orders: pd.DataFrame) -> pd.DataFrame:
    """Durée (jours) de chaque étape pour les commandes livrées.

    Les commandes dont une date manque ou dont les dates sont dans le désordre
    (par exemple remise au transporteur avant la validation, ~1,5 % des
    livraisons) sont écartées : leurs durées ne sont pas fiables.
    """
    done = delivered(orders)
    steps = [
        "purchase_date",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
    ]
    durations = pd.DataFrame(
        {
            stage: (done[end] - done[begin]).dt.total_seconds() / 86_400
            for stage, begin, end in zip(STAGES, steps, steps[1:])
        }
    )
    valid = durations.notna().all(axis=1) & (durations >= 0).all(axis=1)
    return durations[valid].assign(purchase_date=done.loc[valid, "purchase_date"])


def _month(dates: pd.Series) -> pd.Series:
    return dates.dt.to_period("M").dt.to_timestamp().rename("month")


def monthly_delivery_stages(orders: pd.DataFrame) -> pd.DataFrame:
    stages = delivery_stages(orders)
    out = stages.groupby(_month(stages["purchase_date"]))[list(STAGES)].mean()
    return out.reset_index()


def monthly_delivery(orders: pd.DataFrame) -> pd.DataFrame:
    """Taux de retard et délai moyen des commandes livrées, par mois d'achat."""
    done = delivered(orders)
    out = done.groupby(_month(done["purchase_date"])).agg(
        late_rate=("is_late", lambda s: s.astype("float").mean()),
        delivery_days=("delivery_days", "mean"),
        delivered=("order_id", "count"),
    )
    return out.reset_index()


# Bornes (jours d'écart à la date estimée) et libellés des tranches.
DELAY_BUCKETS = [
    (-float("inf"), -8, "En avance de 8 j ou +"),
    (-7, -1, "En avance de 1 à 7 j"),
    (0, 0, "Le jour prévu"),
    (1, 3, "Retard de 1 à 3 j"),
    (4, 7, "Retard de 4 à 7 j"),
    (8, 14, "Retard de 8 à 14 j"),
    (15, float("inf"), "Retard de 15 j ou +"),
]


def review_by_delay(orders: pd.DataFrame) -> pd.DataFrame:
    """Note moyenne des commandes livrées selon leur écart à la date estimée."""
    done = delivered(orders).dropna(subset=["review_score"])
    rows = []
    for low, high, label in DELAY_BUCKETS:
        bucket = done[done["delay_days"].between(low, high)]
        rows.append(
            {
                "bucket": label,
                "review_score": _mean(bucket["review_score"]),
                "orders": len(bucket),
                "low_scores": _mean((bucket["review_score"] <= 2).astype("float")),
            }
        )
    return pd.DataFrame(rows)


def low_score_rate(orders: pd.DataFrame, min_delay: float, max_delay: float) -> float | None:
    """Part des notes de 1 ou 2 parmi les commandes livrées avec un écart dans [min, max] jours."""
    done = delivered(orders).dropna(subset=["review_score"])
    scores = done.loc[done["delay_days"].between(min_delay, max_delay), "review_score"]
    return _mean((scores <= 2).astype("float"))


def logistics_by_state(orders: pd.DataFrame) -> pd.DataFrame:
    """Indicateurs de livraison par État du client, du plus lent au plus rapide."""
    done = delivered(orders)
    out = done.groupby("customer_state").agg(
        delivery_days=("delivery_days", "mean"),
        late_rate=("is_late", lambda s: s.astype("float").mean()),
        freight_value=("freight_value", "mean"),
        review_score=("review_score", "mean"),
        delivered=("order_id", "count"),
    )
    return out.sort_values("delivery_days", ascending=False).reset_index()
