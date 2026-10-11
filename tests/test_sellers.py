import pandas as pd
import pytest

from olist_dashboard import metrics


@pytest.fixture
def orders():
    return pd.DataFrame(
        {
            "order_id": ["o1", "o2", "o3", "o4"],
            "order_status": ["delivered", "delivered", "delivered", "canceled"],
            "review_score": [5.0, 1.0, 4.0, 1.0],
            "is_late": pd.array([False, True, False, pd.NA], dtype="boolean"),
        }
    )


@pytest.fixture
def items():
    # o2 contient des articles de deux vendeurs ; o4 est annulée.
    return pd.DataFrame(
        {
            "order_id": ["o1", "o1", "o2", "o2", "o3", "o4"],
            "seller_id": ["s1", "s1", "s1", "s2", "s3", "s3"],
            "seller_state": ["SP", "SP", "SP", "PR", "SP", "SP"],
            "category": ["Toys", "Toys", "Auto", "Toys", "Auto", "Auto"],
            "price": [100.0, 100.0, 50.0, 30.0, 10.0, 999.0],
            "freight_value": [10.0, 10.0, 5.0, 3.0, 2.0, 0.0],
            "order_status": ["delivered"] * 5 + ["canceled"],
        }
    )


def test_seller_stats(orders, items):
    out = metrics.seller_stats(orders, items).set_index("seller_id")
    assert out.index.tolist() == ["s1", "s2", "s3"]  # CA décroissant
    assert out.loc["s1", "revenue"] == 275.0
    assert out.loc["s1", "orders"] == 2
    assert out.loc["s1", "items"] == 3
    assert out.loc["s1", "review_score"] == 3.0  # une note par commande, pas par article
    assert out.loc["s1", "late_rate"] == 0.5
    assert out.loc["s2", "review_score"] == 1.0  # la note de o2 compte aussi pour s2
    assert out.loc["s3", "revenue"] == 12.0  # commande annulée exclue


def test_top_share():
    sellers = pd.DataFrame({"revenue": [60.0, 20.0, 10.0, 5.0, 5.0]})
    assert metrics.top_share(sellers, 0.2) == pytest.approx(0.6)
    assert metrics.top_share(sellers, 0.01) == pytest.approx(0.6)  # au moins un vendeur
    assert metrics.top_share(sellers.iloc[0:0], 0.1) is None


def test_compute_seller_kpis(orders, items):
    kpis = metrics.compute_seller_kpis(orders, items)
    assert kpis.active_sellers == 3
    assert kpis.median_revenue == 33.0
    assert kpis.small_seller_share == 1.0
    assert kpis.categories == 2
    assert kpis.average_item_price == pytest.approx(58.0)


def test_concentration_curve():
    sellers = pd.DataFrame({"revenue": [10.0, 30.0, 60.0]})
    out = metrics.concentration_curve(sellers)
    assert out["seller_share"].tolist() == pytest.approx([0, 1 / 3, 2 / 3, 1])
    assert out["revenue_share"].tolist() == pytest.approx([0, 0.6, 0.9, 1.0])


def test_concentration_curve_is_downsampled():
    sellers = pd.DataFrame({"revenue": [1.0] * 1_000})
    out = metrics.concentration_curve(sellers, points=50)
    assert len(out) == 50
    assert out.iloc[-1].tolist() == [1.0, 1.0]


def test_revenue_by_seller_state(items):
    out = metrics.revenue_by_seller_state(items)
    assert out["seller_state"].tolist() == ["SP", "PR"]
    assert out["sellers"].tolist() == [2, 1]
    assert out["revenue"].tolist() == [287.0, 33.0]


def test_category_stats(orders, items):
    out = metrics.category_stats(orders, items).set_index("category")
    assert out.loc["Toys", "revenue"] == 253.0
    assert out.loc["Toys", "orders"] == 2
    assert out.loc["Toys", "sellers"] == 2
    assert out.loc["Toys", "review_score"] == 3.0
    assert out.loc["Auto", "reviews"] == 2  # o4 annulée exclue
    assert out["share"].sum() == pytest.approx(1.0)
