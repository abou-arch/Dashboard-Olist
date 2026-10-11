"""Calcul des indicateurs à partir des tables ``orders`` et ``items``."""

from dataclasses import dataclass

import numpy as np
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


# --- Satisfaction ------------------------------------------------------------


def reviewed(orders: pd.DataFrame) -> pd.DataFrame:
    """Commandes qui ont reçu au moins un avis, avec leur note arrondie (1 à 5).

    Une commande notée plusieurs fois a pour note la moyenne de ses avis ;
    l'arrondi (4,5 -> 5) la range dans une seule étoile.
    """
    out = orders.dropna(subset=["review_score"])
    stars = np.floor(out["review_score"] + 0.5).astype("int64")
    return out.assign(stars=stars)


@dataclass(frozen=True)
class SatisfactionKpis:
    reviewed: int
    response_rate: float | None
    average_review: float | None
    satisfied_share: float | None
    dissatisfied_share: float | None
    comment_rate: float | None
    dissatisfied_comment_rate: float | None


def compute_satisfaction_kpis(orders: pd.DataFrame) -> SatisfactionKpis:
    rated = reviewed(orders)
    unhappy = rated[rated["stars"] <= 2]
    return SatisfactionKpis(
        reviewed=len(rated),
        response_rate=len(rated) / len(orders) if len(orders) else None,
        average_review=_mean(rated["review_score"]),
        satisfied_share=_mean((rated["stars"] >= 4).astype("float")),
        dissatisfied_share=_mean((rated["stars"] <= 2).astype("float")),
        comment_rate=_mean(rated["has_comment"].astype("float")),
        dissatisfied_comment_rate=_mean(unhappy["has_comment"].astype("float")),
    )


def score_distribution(orders: pd.DataFrame) -> pd.DataFrame:
    """Nombre et part des commandes par note, de 5 à 1 étoile."""
    rated = reviewed(orders)
    counts = rated["stars"].value_counts().reindex(range(5, 0, -1), fill_value=0)
    out = counts.rename("orders").rename_axis("stars").reset_index()
    total = out["orders"].sum()
    out["share"] = out["orders"] / total if total else 0.0
    out["label"] = out["stars"].map(lambda n: f"{n} ★")
    return out


def monthly_satisfaction(orders: pd.DataFrame) -> pd.DataFrame:
    rated = reviewed(orders)
    out = rated.groupby(_month(rated["purchase_date"])).agg(
        review_score=("review_score", "mean"),
        dissatisfied_share=("stars", lambda s: (s <= 2).mean()),
        reviewed=("order_id", "count"),
    )
    return out.reset_index()


def _review_groups(rated: pd.DataFrame, groups: dict[str, pd.Series]) -> pd.DataFrame:
    rows = [
        {
            "group": label,
            "review_score": _mean(rated.loc[mask, "review_score"]),
            "dissatisfied_share": _mean((rated.loc[mask, "stars"] <= 2).astype("float")),
            "orders": int(mask.sum()),
        }
        for label, mask in groups.items()
    ]
    return pd.DataFrame(rows)


def review_by_delivery(orders: pd.DataFrame) -> pd.DataFrame:
    """Note moyenne selon que la commande a été livrée à temps, en retard ou pas livrée."""
    rated = reviewed(orders)
    is_delivered = rated["order_status"] == "delivered"
    return _review_groups(
        rated,
        {
            "Livrée à temps": is_delivered & (rated["delay_days"] <= 0),
            "Livrée en retard": is_delivered & (rated["delay_days"] > 0),
            "Non livrée": ~is_delivered,
        },
    )


def review_by_items(orders: pd.DataFrame) -> pd.DataFrame:
    """Note moyenne selon le nombre d'articles de la commande."""
    rated = reviewed(orders)
    n = rated["n_items"]
    return _review_groups(
        rated, {"1 article": n == 1, "2 articles": n == 2, "3 articles ou +": n >= 3}
    )


def review_by_category(orders: pd.DataFrame, items: pd.DataFrame) -> pd.DataFrame:
    """Note moyenne par catégorie de produit, de la moins bien à la mieux notée.

    Une commande compte une fois dans chaque catégorie de produits qu'elle contient.
    """
    rated = reviewed(orders)[["order_id", "review_score", "stars"]]
    pairs = items[["order_id", "category"]].drop_duplicates().merge(rated, on="order_id")
    out = pairs.groupby("category").agg(
        review_score=("review_score", "mean"),
        dissatisfied_share=("stars", lambda s: (s <= 2).mean()),
        orders=("order_id", "count"),
    )
    return out.sort_values("review_score").reset_index()


def min_reviews_for_ranking(n_reviews: int) -> int:
    """Nombre d'avis minimum pour classer une catégorie (0,3 % des avis, au moins 20)."""
    return max(20, round(n_reviews * 0.003))


# --- Vendeurs et catégories --------------------------------------------------


def _with_outcomes(items: pd.DataFrame, orders: pd.DataFrame, key: str) -> pd.DataFrame:
    """Couples (``key``, commande) distincts, avec la note et le retard de la commande.

    La note et le retard concernent toute la commande : une commande de
    plusieurs vendeurs (≈ 1 %) compte pour chacun d'eux.
    """
    pairs = items[[key, "order_id"]].drop_duplicates()
    outcomes = orders.set_index("order_id")[["review_score", "is_late"]]
    return pairs.join(outcomes, on="order_id")


def _late_rate(series: pd.Series) -> float:
    return series.dropna().astype("float").mean()


def seller_stats(orders: pd.DataFrame, items: pd.DataFrame) -> pd.DataFrame:
    """Indicateurs par vendeur, du plus gros CA au plus petit."""
    sales = sold(items)
    sales = sales.assign(revenue=sales["price"] + sales["freight_value"])
    out = sales.groupby("seller_id").agg(
        seller_state=("seller_state", "first"),
        revenue=("revenue", "sum"),
        orders=("order_id", "nunique"),
        items=("order_id", "count"),
        average_price=("price", "mean"),
    )
    outcomes = _with_outcomes(sales, orders, "seller_id").groupby("seller_id").agg(
        review_score=("review_score", "mean"), late_rate=("is_late", _late_rate)
    )
    out = out.join(outcomes)
    return out.sort_values("revenue", ascending=False).reset_index()


def top_share(sellers: pd.DataFrame, fraction: float) -> float | None:
    """Part du CA réalisée par la fraction ``fraction`` des vendeurs les plus gros."""
    if sellers.empty or not sellers["revenue"].sum():
        return None
    n = max(1, int(np.ceil(len(sellers) * fraction)))
    revenue = sellers["revenue"].sort_values(ascending=False)
    return float(revenue.head(n).sum() / revenue.sum())


@dataclass(frozen=True)
class SellerKpis:
    active_sellers: int
    median_revenue: float | None
    top10_share: float | None
    small_seller_share: float | None
    categories: int
    average_item_price: float | None


SMALL_SELLER_ORDERS = 10


def compute_seller_kpis(orders: pd.DataFrame, items: pd.DataFrame) -> SellerKpis:
    sellers = seller_stats(orders, items)
    sales = sold(items)
    return SellerKpis(
        active_sellers=len(sellers),
        median_revenue=_median(sellers["revenue"]),
        top10_share=top_share(sellers, 0.10),
        small_seller_share=_mean((sellers["orders"] < SMALL_SELLER_ORDERS).astype("float")),
        categories=int(sales["category"].nunique()),
        average_item_price=_mean(sales["price"]),
    )


def concentration_curve(sellers: pd.DataFrame, points: int = 200) -> pd.DataFrame:
    """Part cumulée du CA selon la part des vendeurs, du plus gros au plus petit."""
    revenue = sellers["revenue"].sort_values(ascending=False).to_numpy()
    if not len(revenue) or not revenue.sum():
        return pd.DataFrame({"seller_share": [], "revenue_share": []})
    cumulative = np.concatenate([[0.0], np.cumsum(revenue) / revenue.sum()])
    seller_share = np.arange(len(cumulative)) / len(revenue)
    keep = np.unique(np.linspace(0, len(cumulative) - 1, min(points, len(cumulative))).round().astype(int))
    return pd.DataFrame({"seller_share": seller_share[keep], "revenue_share": cumulative[keep]})


def revenue_by_seller_state(items: pd.DataFrame, top: int = 10) -> pd.DataFrame:
    sales = sold(items)
    sales = sales.assign(revenue=sales["price"] + sales["freight_value"])
    out = sales.groupby("seller_state").agg(
        revenue=("revenue", "sum"), sellers=("seller_id", "nunique")
    )
    out["share"] = out["revenue"] / out["revenue"].sum()
    return out.sort_values("revenue", ascending=False).head(top).reset_index()


def category_stats(orders: pd.DataFrame, items: pd.DataFrame) -> pd.DataFrame:
    """Indicateurs par catégorie de produit, du plus gros CA au plus petit."""
    sales = sold(items)
    sales = sales.assign(revenue=sales["price"] + sales["freight_value"])
    out = sales.groupby("category").agg(
        revenue=("revenue", "sum"),
        orders=("order_id", "nunique"),
        sellers=("seller_id", "nunique"),
        average_price=("price", "mean"),
    )
    out["share"] = out["revenue"] / out["revenue"].sum()
    outcomes = _with_outcomes(sales, orders, "category").groupby("category").agg(
        review_score=("review_score", "mean"),
        reviews=("review_score", "count"),
        late_rate=("is_late", _late_rate),
    )
    out = out.join(outcomes)
    return out.sort_values("revenue", ascending=False).reset_index()


# --- Clients -----------------------------------------------------------------

PAYMENT_LABELS = {
    "credit_card": "Carte de crédit",
    "boleto": "Boleto",
    "voucher": "Bon d'achat",
    "debit_card": "Carte de débit",
    "not_defined": "Non défini",
}


@dataclass(frozen=True)
class CustomerKpis:
    customers: int
    repeat_rate: float | None
    orders_per_customer: float | None
    revenue_per_customer: float | None
    credit_card_share: float | None
    average_installments: float | None


def compute_customer_kpis(orders: pd.DataFrame) -> CustomerKpis:
    """Indicateurs clients sur les commandes vendues de la période.

    Un client (``customer_unique_id``) qui revient a plusieurs ``customer_id``
    chez Olist ; c'est bien l'identifiant unique qui est compté.
    """
    sales = sold(orders)
    per_customer = sales.groupby("customer_unique_id")["order_id"].count()
    card = sales[sales["payment_type"] == "credit_card"]
    customers = len(per_customer)
    return CustomerKpis(
        customers=customers,
        repeat_rate=_mean((per_customer > 1).astype("float")),
        orders_per_customer=_mean(per_customer.astype("float")),
        revenue_per_customer=float(sales["revenue"].sum() / customers) if customers else None,
        credit_card_share=_mean((sales["payment_type"] == "credit_card").astype("float")),
        average_installments=_mean(card["payment_installments"].astype("float")),
    )


def customers_by_order_count(orders: pd.DataFrame) -> pd.DataFrame:
    """Nombre de clients selon leur nombre de commandes sur la période (1, 2, 3 ou +)."""
    per_customer = sold(orders).groupby("customer_unique_id")["order_id"].count()
    groups = {
        "1 commande": per_customer == 1,
        "2 commandes": per_customer == 2,
        "3 commandes ou +": per_customer >= 3,
    }
    out = pd.DataFrame({"group": list(groups), "customers": [int(m.sum()) for m in groups.values()]})
    total = out["customers"].sum()
    out["share"] = out["customers"] / total if total else 0.0
    return out


def payment_mix(orders: pd.DataFrame) -> pd.DataFrame:
    """Commandes, part et panier moyen par moyen de paiement principal."""
    sales = sold(orders).dropna(subset=["payment_type"])
    out = sales.groupby("payment_type").agg(orders=("order_id", "count"), basket=("revenue", "mean"))
    out["share"] = out["orders"] / out["orders"].sum()
    out = out.sort_values("orders", ascending=False).reset_index()
    out["label"] = out["payment_type"].map(PAYMENT_LABELS).fillna(out["payment_type"])
    return out


INSTALLMENT_BUCKETS = [(0, 1, "1 fois"), (2, 3, "2 à 3 fois"), (4, 6, "4 à 6 fois"),
                       (7, 9, "7 à 9 fois"), (10, float("inf"), "10 fois ou +")]


def installments_distribution(orders: pd.DataFrame) -> pd.DataFrame:
    """Commandes payées par carte de crédit selon le nombre de mensualités."""
    card = sold(orders)
    card = card[card["payment_type"] == "credit_card"]
    rows = []
    for low, high, label in INSTALLMENT_BUCKETS:
        bucket = card[card["payment_installments"].between(low, high)]
        rows.append({"group": label, "orders": len(bucket), "basket": _mean(bucket["revenue"])})
    out = pd.DataFrame(rows)
    total = out["orders"].sum()
    out["share"] = out["orders"] / total if total else 0.0
    return out


WEEKDAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


def purchase_heatmap(orders: pd.DataFrame) -> pd.DataFrame:
    """Nombre de commandes par jour de la semaine (lignes) et heure d'achat (colonnes)."""
    dates = sold(orders)["purchase_date"]
    counts = pd.crosstab(dates.dt.dayofweek, dates.dt.hour)
    counts = counts.reindex(index=range(7), columns=range(24), fill_value=0)
    counts.index = WEEKDAYS
    return counts


def revenue_by_city(orders: pd.DataFrame) -> pd.DataFrame:
    """CA, clients et position moyenne par ville, du plus gros CA au plus petit."""
    sales = sold(orders)
    out = sales.groupby(["customer_city", "customer_state"]).agg(
        revenue=("revenue", "sum"),
        customers=("customer_unique_id", "nunique"),
        lat=("customer_lat", "mean"),
        lng=("customer_lng", "mean"),
    )
    out["share"] = out["revenue"] / out["revenue"].sum()
    out = out.sort_values("revenue", ascending=False).reset_index()
    # « sao paulo » -> « Sao Paulo »
    out["city"] = out["customer_city"].str.title() + " (" + out["customer_state"] + ")"
    return out
