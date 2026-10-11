"""Données de chaque page de l'application web, à partir d'une sélection.

Chaque fonction reçoit les tables et la sélection (période, États, période de
comparaison) et renvoie un dictionnaire prêt à être sérialisé en JSON. Les
calculs sont ceux de ``olist_dashboard.metrics`` : l'application Streamlit
affiche les mêmes chiffres.
"""

from collections.abc import Callable
from typing import Any

import pandas as pd

from api.serialize import clean
from olist_dashboard import metrics
from olist_dashboard.selection import Selection

Tables = dict[str, pd.DataFrame]


def _compare(compute: Callable, selection: Selection, *args) -> dict[str, Any]:
    """Indicateurs de la période et, si elle existe, de la période précédente."""
    previous = None
    if selection.previous_orders is not None:
        previous = compute(selection.previous_orders, *args)
    return {"kpis": compute(selection.orders, *args), "previous_kpis": previous}


def _compare_with_items(compute: Callable, tables: Tables, selection: Selection) -> dict[str, Any]:
    """Comme ``_compare``, pour un calcul qui a aussi besoin des articles."""
    previous = None
    if selection.previous_orders is not None:
        previous = compute(selection.previous_orders, selection.previous_items(tables["items"]))
    return {"kpis": compute(selection.orders, selection.items(tables["items"])), "previous_kpis": previous}


def _dashboard_kpis(orders: pd.DataFrame) -> dict[str, Any]:
    kpis = metrics.compute_kpis(orders)
    return {
        "revenue": kpis.revenue,
        "orders": kpis.orders,
        "customers": kpis.customers,
        "average_review": kpis.average_review,
        "reviews": metrics.compute_satisfaction_kpis(orders).reviewed,
    }


def dashboard(tables: Tables, selection: Selection) -> dict[str, Any]:
    current = selection.orders
    logistics = metrics.compute_logistics_kpis(current)
    return clean(
        {
            **_compare(_dashboard_kpis, selection),
            "monthly": metrics.monthly_sales(current),
            "monthly_reviews": metrics.monthly_satisfaction(current)[["month", "review_score"]],
            "by_state": metrics.revenue_by_state(current, top=None),
            "categories": metrics.revenue_by_category(selection.items(tables["items"]), top=5),
            "statuses": metrics.order_status_breakdown(current),
            "delivery_histogram": metrics.delivery_days_histogram(current),
            "median_delivery_days": logistics.median_delivery_days,
        }
    )


def _sales_kpis(orders: pd.DataFrame) -> dict[str, Any]:
    kpis = metrics.compute_kpis(orders)
    customers = metrics.compute_customer_kpis(orders)
    return {
        "revenue": kpis.revenue,
        "orders": kpis.orders,
        "average_basket": kpis.average_basket,
        "freight_share": metrics.compute_logistics_kpis(orders).freight_share,
        "credit_card_share": customers.credit_card_share,
        "average_installments": customers.average_installments,
    }


def sales(tables: Tables, selection: Selection) -> dict[str, Any]:
    current = selection.orders
    return clean(
        {
            **_compare(_sales_kpis, selection),
            "monthly": metrics.monthly_sales(current),
            "payments": metrics.payment_mix(current),
            "installments": metrics.installments_distribution(current),
        }
    )


def customers(tables: Tables, selection: Selection) -> dict[str, Any]:
    current = selection.orders
    heatmap = metrics.purchase_heatmap(current)
    return clean(
        {
            **_compare(metrics.compute_customer_kpis, selection),
            "monthly": metrics.monthly_sales(current)[["month", "customers", "orders"]],
            "loyalty": metrics.customers_by_order_count(current),
            "heatmap": {
                "days": list(heatmap.index),
                "hours": [int(h) for h in heatmap.columns],
                "values": heatmap.to_numpy().tolist(),
            },
        }
    )


def products(tables: Tables, selection: Selection) -> dict[str, Any]:
    current = selection.orders
    current_items = selection.items(tables["items"])
    stats = metrics.seller_stats(current, current_items)
    watched = stats[stats["orders"] >= metrics.WATCH_MIN_ORDERS].dropna(subset=["review_score"])
    categories = metrics.category_stats(current, current_items)
    return clean(
        {
            **_compare_with_items(metrics.compute_seller_kpis, tables, selection),
            "categories": categories,
            "category_threshold": metrics.min_reviews_for_ranking(int(categories["reviews"].sum())),
            "average_review": metrics.compute_kpis(current).average_review,
            "concentration": metrics.concentration_curve(stats),
            "top_sellers": stats.head(10),
            "watched_sellers": watched.sort_values("review_score").head(10),
            "watched_count": len(watched),
            "watch_min_orders": metrics.WATCH_MIN_ORDERS,
            "small_seller_orders": metrics.SMALL_SELLER_ORDERS,
        }
    )


def geography(tables: Tables, selection: Selection) -> dict[str, Any]:
    current = selection.orders
    cities = metrics.revenue_by_city(current)
    by_state = metrics.revenue_by_state(current, top=None)
    delivery = metrics.logistics_by_state(current)[["customer_state", "delivery_days", "late_rate", "freight_value"]]
    return clean(
        {
            "by_state": by_state.merge(delivery, on="customer_state", how="left"),
            "by_seller_state": metrics.revenue_by_seller_state(selection.items(tables["items"])),
            "cities": cities[["city", "revenue", "customers", "share", "lat", "lng"]].round(
                {"lat": 3, "lng": 3, "revenue": 2, "share": 5}
            ),
        }
    )


def satisfaction(tables: Tables, selection: Selection) -> dict[str, Any]:
    current = selection.orders
    compared = _compare(metrics.compute_satisfaction_kpis, selection)
    categories = metrics.review_by_category(current, selection.items(tables["items"]))
    return clean(
        {
            **compared,
            "monthly": metrics.monthly_satisfaction(current),
            "distribution": metrics.score_distribution(current),
            "by_delivery": metrics.review_by_delivery(current),
            "by_items": metrics.review_by_items(current),
            "categories": categories,
            "category_threshold": metrics.min_reviews_for_ranking(compared["kpis"].reviewed),
        }
    )


def deliveries(tables: Tables, selection: Selection) -> dict[str, Any]:
    current = selection.orders
    return clean(
        {
            **_compare(metrics.compute_logistics_kpis, selection),
            "monthly": metrics.monthly_delivery(current),
            "stages": metrics.monthly_delivery_stages(current),
            "stage_labels": metrics.STAGES,
            "histogram": metrics.delivery_days_histogram(current),
            "review_by_delay": metrics.review_by_delay(current),
            "low_score_rates": {
                "very_late": metrics.low_score_rate(current, 4, float("inf")),
                "early": metrics.low_score_rate(current, -float("inf"), -1),
            },
            "by_state": metrics.logistics_by_state(current),
        }
    )


PAGES = {
    "dashboard": dashboard,
    "sales": sales,
    "customers": customers,
    "products": products,
    "geography": geography,
    "satisfaction": satisfaction,
    "deliveries": deliveries,
}
