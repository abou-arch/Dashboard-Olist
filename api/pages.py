"""Données de chaque page du dashboard, à partir d'une sélection.

Chaque fonction reçoit les tables et la sélection (période, États, période de
comparaison) et renvoie un dictionnaire prêt à être sérialisé en JSON. Elles
reprennent les calculs des pages Streamlit : les deux interfaces affichent
les mêmes chiffres.
"""

from typing import Any

import pandas as pd

from api.serialize import clean
from olist_dashboard import metrics
from olist_dashboard.selection import Selection


def _kpis(compute, selection: Selection, *args) -> dict[str, Any]:
    """Indicateurs de la période et, si elle existe, de la période précédente."""
    previous = None
    if selection.previous_orders is not None:
        previous = compute(selection.previous_orders, *args)
    return {"kpis": compute(selection.orders, *args), "previous_kpis": previous}


def overview(tables: dict[str, pd.DataFrame], selection: Selection) -> dict[str, Any]:
    current_items = selection.items(tables["items"])
    return clean(
        {
            **_kpis(metrics.compute_kpis, selection),
            "monthly": metrics.monthly_sales(selection.orders),
            "categories": metrics.revenue_by_category(current_items),
            "by_state": metrics.revenue_by_state(selection.orders),
        }
    )


def logistics(tables: dict[str, pd.DataFrame], selection: Selection) -> dict[str, Any]:
    current = selection.orders
    return clean(
        {
            **_kpis(metrics.compute_logistics_kpis, selection),
            "monthly": metrics.monthly_delivery(current),
            "stages": metrics.monthly_delivery_stages(current),
            "stage_labels": metrics.STAGES,
            "review_by_delay": metrics.review_by_delay(current),
            "low_score_rates": {
                "very_late": metrics.low_score_rate(current, 4, float("inf")),
                "early": metrics.low_score_rate(current, -float("inf"), -1),
            },
            "by_state": metrics.logistics_by_state(current),
        }
    )


def satisfaction(tables: dict[str, pd.DataFrame], selection: Selection) -> dict[str, Any]:
    current = selection.orders
    kpis = _kpis(metrics.compute_satisfaction_kpis, selection)
    categories = metrics.review_by_category(current, selection.items(tables["items"]))
    return clean(
        {
            **kpis,
            "monthly": metrics.monthly_satisfaction(current),
            "distribution": metrics.score_distribution(current),
            "by_delivery": metrics.review_by_delivery(current),
            "by_items": metrics.review_by_items(current),
            "categories": categories,
            "category_threshold": metrics.min_reviews_for_ranking(kpis["kpis"].reviewed),
        }
    )


def sellers(tables: dict[str, pd.DataFrame], selection: Selection) -> dict[str, Any]:
    current = selection.orders
    current_items = selection.items(tables["items"])
    previous = None
    if selection.previous_orders is not None:
        previous = metrics.compute_seller_kpis(
            selection.previous_orders, selection.previous_items(tables["items"])
        )
    stats = metrics.seller_stats(current, current_items)
    watched = stats[stats["orders"] >= metrics.WATCH_MIN_ORDERS].dropna(subset=["review_score"])
    categories = metrics.category_stats(current, current_items)
    return clean(
        {
            "kpis": metrics.compute_seller_kpis(current, current_items),
            "previous_kpis": previous,
            "concentration": metrics.concentration_curve(stats),
            "by_seller_state": metrics.revenue_by_seller_state(current_items),
            "categories": categories,
            "category_threshold": metrics.min_reviews_for_ranking(int(categories["reviews"].sum())),
            "average_review": metrics.compute_kpis(current).average_review,
            "top_sellers": stats.head(10),
            "watched_sellers": watched.sort_values("review_score").head(10),
            "watched_count": len(watched),
            "watch_min_orders": metrics.WATCH_MIN_ORDERS,
            "small_seller_orders": metrics.SMALL_SELLER_ORDERS,
        }
    )


def customers(tables: dict[str, pd.DataFrame], selection: Selection) -> dict[str, Any]:
    current = selection.orders
    heatmap = metrics.purchase_heatmap(current)
    cities = metrics.revenue_by_city(current)
    return clean(
        {
            **_kpis(metrics.compute_customer_kpis, selection),
            "loyalty": metrics.customers_by_order_count(current),
            "payments": metrics.payment_mix(current),
            "installments": metrics.installments_distribution(current),
            "heatmap": {
                "days": list(heatmap.index),
                "hours": [int(h) for h in heatmap.columns],
                "values": heatmap.to_numpy().tolist(),
            },
            "cities": cities[["city", "revenue", "customers", "share", "lat", "lng"]].round(
                {"lat": 3, "lng": 3, "revenue": 2, "share": 5}
            ),
        }
    )


PAGES = {
    "overview": overview,
    "logistics": logistics,
    "satisfaction": satisfaction,
    "sellers": sellers,
    "customers": customers,
}
