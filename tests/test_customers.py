import pandas as pd
import pytest

from olist_dashboard import metrics


@pytest.fixture
def orders():
    # u1 commande deux fois ; la commande annulée de u3 ne compte pas.
    return pd.DataFrame(
        {
            "order_id": ["a", "b", "c", "d", "e"],
            "customer_unique_id": ["u1", "u1", "u2", "u3", "u4"],
            "customer_city": ["sao paulo", "sao paulo", "rio de janeiro", "sao paulo", "sao paulo"],
            "customer_state": ["SP", "SP", "RJ", "SP", "SP"],
            "customer_lat": [-23.5, -23.6, -22.9, -23.5, -23.4],
            "customer_lng": [-46.6, -46.6, -43.2, -46.6, -46.6],
            "order_status": ["delivered", "delivered", "delivered", "canceled", "shipped"],
            # Lundi 10h, lundi 10h, mardi 15h, mercredi 9h, dimanche 23h.
            "purchase_date": pd.to_datetime(
                ["2018-01-01 10:05", "2018-01-01 10:40", "2018-01-02 15:00",
                 "2018-01-03 09:00", "2018-01-07 23:59"]
            ),
            "revenue": [100.0, 50.0, 300.0, 999.0, 30.0],
            "payment_type": ["credit_card", "boleto", "credit_card", "credit_card", "voucher"],
            "payment_installments": [1, 1, 10, 4, 1],
        }
    )


def test_compute_customer_kpis(orders):
    kpis = metrics.compute_customer_kpis(orders)
    assert kpis.customers == 3
    assert kpis.repeat_rate == pytest.approx(1 / 3)
    assert kpis.orders_per_customer == pytest.approx(4 / 3)
    assert kpis.revenue_per_customer == pytest.approx(160.0)
    assert kpis.credit_card_share == 0.5
    assert kpis.average_installments == 5.5


def test_customers_by_order_count(orders):
    out = metrics.customers_by_order_count(orders)
    assert out["customers"].tolist() == [2, 1, 0]
    assert out["share"].sum() == pytest.approx(1.0)


def test_payment_mix(orders):
    out = metrics.payment_mix(orders).set_index("payment_type")
    assert out.index[0] == "credit_card"
    assert out.loc["credit_card", "orders"] == 2
    assert out.loc["credit_card", "basket"] == 200.0
    assert out.loc["voucher", "label"] == "Bon d'achat"


def test_installments_distribution(orders):
    out = metrics.installments_distribution(orders).set_index("group")
    assert out.loc["1 fois", "orders"] == 1
    assert out.loc["10 fois ou +", "basket"] == 300.0
    assert out.loc["4 à 6 fois", "orders"] == 0  # commande annulée exclue
    assert pd.isna(out.loc["4 à 6 fois", "basket"]) or out.loc["4 à 6 fois", "basket"] is None


def test_purchase_heatmap(orders):
    out = metrics.purchase_heatmap(orders)
    assert out.shape == (7, 24)
    assert out.loc["Lundi", 10] == 2
    assert out.loc["Dimanche", 23] == 1
    assert out.loc["Mercredi", 9] == 0  # commande annulée
    assert out.to_numpy().sum() == 4


def test_revenue_by_city(orders):
    out = metrics.revenue_by_city(orders)
    assert out["city"].tolist() == ["Rio De Janeiro (RJ)", "Sao Paulo (SP)"]
    sp = out.set_index("city").loc["Sao Paulo (SP)"]
    assert sp["revenue"] == 180.0
    assert sp["customers"] == 2
    assert sp["lat"] == pytest.approx(-23.5)
