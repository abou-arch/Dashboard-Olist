import pandas as pd
import pytest

from olist_dashboard.config import UNKNOWN_CATEGORY
from olist_dashboard.data import build_categories, build_items, build_orders, format_category


@pytest.fixture
def raw():
    ts = pd.Timestamp
    orders = pd.DataFrame(
        {
            "order_id": ["o1", "o2", "o3"],
            "customer_id": ["c1", "c2", "c3"],
            "order_status": ["delivered", "delivered", "canceled"],
            "order_purchase_timestamp": [ts("2017-03-01 10:00"), ts("2017-03-02 08:00"), ts("2017-03-03")],
            "order_approved_at": [ts("2017-03-01 11:00"), ts("2017-03-02 09:00"), pd.NaT],
            "order_delivered_carrier_date": [ts("2017-03-02"), ts("2017-03-03"), pd.NaT],
            # o1 : livrée le jour estimé (à l'heure) ; o2 : livrée un jour après (en retard).
            "order_delivered_customer_date": [ts("2017-03-10 23:00"), ts("2017-03-11 01:00"), pd.NaT],
            "order_estimated_delivery_date": [ts("2017-03-10"), ts("2017-03-10"), ts("2017-03-20")],
        }
    )
    items = pd.DataFrame(
        {
            "order_id": ["o1", "o1", "o2"],
            "order_item_id": [1, 2, 1],
            "product_id": ["p1", "p2", "p3"],
            "seller_id": ["s1", "s1", "s2"],
            "shipping_limit_date": [ts("2017-03-02")] * 3,
            "price": [10.0, 20.0, 50.0],
            "freight_value": [1.0, 2.0, 5.0],
        }
    )
    customers = pd.DataFrame(
        {
            "customer_id": ["c1", "c2", "c3"],
            "customer_unique_id": ["u1", "u2", "u1"],
            "customer_zip_code_prefix": ["01000", "20000", "01000"],
            "customer_city": ["sao paulo", "rio de janeiro", "sao paulo"],
            "customer_state": ["SP", "RJ", "SP"],
        }
    )
    reviews = pd.DataFrame(
        {
            "review_id": ["r1", "r2", "r3"],
            "order_id": ["o1", "o1", "o2"],
            "review_score": [4, 5, 1],
        }
    )
    products = pd.DataFrame(
        {
            "product_id": ["p1", "p2", "p3"],
            "product_category_name": ["beleza_saude", "pc_gamer", None],
        }
    )
    translation = pd.DataFrame(
        {
            "product_category_name": ["beleza_saude"],
            "product_category_name_english": ["health_beauty"],
        }
    )
    return dict(
        orders=orders, items=items, customers=customers,
        reviews=reviews, products=products, translation=translation,
    )


def test_format_category():
    assert format_category("health_beauty") == "Health beauty"


def test_build_categories_handles_missing_translations(raw):
    categories = build_categories(raw["products"], raw["translation"])
    assert categories.to_dict() == {"p1": "Health beauty", "p2": "Pc gamer", "p3": UNKNOWN_CATEGORY}


def test_build_orders_amounts_and_reviews(raw):
    orders = build_orders(raw["orders"], raw["items"], raw["customers"], raw["reviews"]).set_index("order_id")
    assert orders.loc["o1", "items_value"] == 30.0
    assert orders.loc["o1", "freight_value"] == 3.0
    assert orders.loc["o1", "revenue"] == 33.0
    assert orders.loc["o1", "n_items"] == 2
    assert orders.loc["o1", "review_score"] == 4.5  # moyenne des deux avis
    # Commande sans article ni avis.
    assert orders.loc["o3", "revenue"] == 0.0
    assert orders.loc["o3", "n_items"] == 0
    assert pd.isna(orders.loc["o3", "review_score"])
    assert orders.loc["o2", "customer_state"] == "RJ"


def test_build_orders_delivery(raw):
    orders = build_orders(raw["orders"], raw["items"], raw["customers"], raw["reviews"]).set_index("order_id")
    assert orders.loc["o1", "is_late"] == False  # noqa: E712 - même jour que l'estimation
    assert orders.loc["o2", "is_late"] == True  # noqa: E712
    assert pd.isna(orders.loc["o3", "is_late"])  # jamais livrée
    assert orders.loc["o1", "delivery_days"] == pytest.approx(9 + 13 / 24)


def test_build_items_adds_order_context(raw):
    orders = build_orders(raw["orders"], raw["items"], raw["customers"], raw["reviews"])
    categories = build_categories(raw["products"], raw["translation"])
    items = build_items(raw["items"], orders, categories)
    assert len(items) == 3
    first = items.iloc[0]
    assert first["category"] == "Health beauty"
    assert first["customer_state"] == "SP"
    assert first["purchase_date"] == pd.Timestamp("2017-03-01 10:00")
