import pandas as pd
import pytest

from olist_dashboard import formatting as fmt
from olist_dashboard import metrics


@pytest.fixture
def orders():
    return pd.DataFrame(
        {
            "order_id": ["a", "b", "c", "d"],
            "customer_unique_id": ["u1", "u1", "u2", "u3"],
            "customer_state": ["SP", "SP", "RJ", "MG"],
            "order_status": ["delivered", "delivered", "shipped", "canceled"],
            "purchase_date": pd.to_datetime(
                ["2017-01-15 10:00", "2017-01-31 23:59", "2017-02-01 00:00", "2017-02-10 00:00"]
            ),
            "revenue": [100.0, 50.0, 30.0, 999.0],
            "review_score": [5.0, 3.0, None, 1.0],
            "delivery_days": [10.0, 20.0, None, None],
            "is_late": pd.array([False, True, pd.NA, pd.NA], dtype="boolean"),
        }
    )


@pytest.fixture
def items():
    return pd.DataFrame(
        {
            "order_id": ["a", "a", "b", "d"],
            "category": ["Toys", "Auto", "Toys", "Auto"],
            "price": [60.0, 30.0, 45.0, 999.0],
            "freight_value": [5.0, 5.0, 5.0, 0.0],
            "order_status": ["delivered", "delivered", "delivered", "canceled"],
        }
    )


def test_filter_orders_includes_whole_end_day(orders):
    out = metrics.filter_orders(orders, "2017-01-01", "2017-01-31")
    assert out["order_id"].tolist() == ["a", "b"]


def test_filter_orders_by_state(orders):
    out = metrics.filter_orders(orders, "2017-01-01", "2017-12-31", ["RJ", "MG"])
    assert out["order_id"].tolist() == ["c", "d"]


def test_compute_kpis_excludes_canceled_from_sales(orders):
    kpis = metrics.compute_kpis(orders)
    assert kpis.revenue == 180.0
    assert kpis.orders == 3
    assert kpis.customers == 2
    assert kpis.average_basket == 60.0
    assert kpis.average_review == 3.0
    assert kpis.late_rate == 0.5
    assert kpis.average_delivery_days == 15.0


def test_compute_kpis_empty(orders):
    kpis = metrics.compute_kpis(orders.iloc[0:0])
    assert kpis.revenue == 0.0
    assert kpis.average_basket is None
    assert kpis.late_rate is None


def test_previous_period_has_same_length():
    start, end = metrics.previous_period(pd.Timestamp("2018-01-01"), pd.Timestamp("2018-01-31"))
    assert (start, end) == (pd.Timestamp("2017-12-01"), pd.Timestamp("2017-12-31"))


def test_monthly_sales(orders):
    out = metrics.monthly_sales(orders)
    assert out["month"].tolist() == [pd.Timestamp("2017-01-01"), pd.Timestamp("2017-02-01")]
    assert out["revenue"].tolist() == [150.0, 30.0]
    assert out["orders"].tolist() == [2, 1]


def test_revenue_by_category(items):
    out = metrics.revenue_by_category(items)
    assert out["category"].tolist() == ["Toys", "Auto"]
    assert out["revenue"].tolist() == [115.0, 35.0]
    assert out["share"].sum() == pytest.approx(1.0)


def test_revenue_by_state(orders):
    out = metrics.revenue_by_state(orders, top=1)
    assert out["customer_state"].tolist() == ["SP"]
    assert out["orders"].tolist() == [2]
    assert out["share"].tolist() == [pytest.approx(150 / 180)]


@pytest.mark.parametrize(
    ("value", "expected"),
    [(1284, "1 284"), (25_400, "25,4 k"), (15_688_396, "15,7 M"), (2.5e9, "2,5 Md")],
)
def test_compact(value, expected):
    assert fmt.compact(value) == expected.replace(" ", fmt.NBSP)


def test_percent():
    assert fmt.percent(0.0679) == f"6,8{fmt.NBSP}%"


def test_signed_number():
    assert fmt.number(1.234, 1, signed=True) == "+1,2"
    assert fmt.number(-1.234, 1, signed=True) == "-1,2"
    assert fmt.number(0.001, 1, signed=True) == "0,0"
