import pandas as pd
import pytest

from olist_dashboard import metrics

ts = pd.Timestamp


@pytest.fixture
def orders():
    """4 commandes livrées (dont 2 en retard), 1 en cours, 1 annulée."""
    purchase = [ts("2018-01-01"), ts("2018-01-10"), ts("2018-02-01"), ts("2018-02-05"),
                ts("2018-02-06"), ts("2018-02-07")]
    approved = [p + pd.Timedelta(days=1) for p in purchase]
    carrier = [a + pd.Timedelta(days=2) for a in approved]
    # Commande 4 : remise au transporteur avant la validation (dates incohérentes).
    carrier[3] = purchase[3]
    customer = [c + pd.Timedelta(days=7) for c in carrier]
    customer[4] = customer[5] = pd.NaT
    return pd.DataFrame(
        {
            "order_id": list("abcdef"),
            "customer_state": ["SP", "SP", "RJ", "RJ", "SP", "MG"],
            "order_status": ["delivered"] * 4 + ["shipped", "canceled"],
            "purchase_date": purchase,
            "order_approved_at": approved,
            "order_delivered_carrier_date": carrier,
            "order_delivered_customer_date": customer,
            "delivery_days": [10.0, 10.0, 10.0, 8.0, None, None],
            "delay_days": [-10.0, 2.0, 0.0, 6.0, None, None],
            "is_late": pd.array([False, True, False, True, pd.NA, pd.NA], dtype="boolean"),
            "review_score": [5.0, 3.0, 4.0, 1.0, None, 1.0],
            "revenue": [100.0, 100.0, 100.0, 100.0, 100.0, 500.0],
            "freight_value": [10.0, 20.0, 10.0, 0.0, 10.0, 50.0],
        }
    )


def test_compute_logistics_kpis(orders):
    kpis = metrics.compute_logistics_kpis(orders)
    assert kpis.delivered == 4
    assert kpis.average_delivery_days == 9.5
    assert kpis.late_rate == 0.5
    assert kpis.average_delay_when_late == 4.0
    assert kpis.median_margin_days == pytest.approx(-1.0)
    assert kpis.average_handling_days == pytest.approx(2.0)
    # Commande annulée exclue : 50 / 500.
    assert kpis.freight_share == pytest.approx(0.1)


def test_delivery_stages_drop_inconsistent_dates(orders):
    stages = metrics.delivery_stages(orders)
    assert len(stages) == 3
    assert stages[list(metrics.STAGES)].iloc[0].tolist() == [1.0, 2.0, 7.0]


def test_monthly_delivery(orders):
    out = metrics.monthly_delivery(orders)
    assert out["month"].tolist() == [ts("2018-01-01"), ts("2018-02-01")]
    assert out["late_rate"].tolist() == [0.5, 0.5]
    assert out["delivered"].tolist() == [2, 2]


def test_review_by_delay(orders):
    out = metrics.review_by_delay(orders).set_index("bucket")
    assert len(out) == len(metrics.DELAY_BUCKETS)
    assert out["orders"].sum() == 4
    assert out.loc["Le jour prévu", "review_score"] == 4.0
    assert out.loc["Retard de 4 à 7 j", "low_scores"] == 1.0
    assert out.loc["Retard de 15 j ou +", "review_score"] is None or pd.isna(
        out.loc["Retard de 15 j ou +", "review_score"]
    )


def test_low_score_rate(orders):
    assert metrics.low_score_rate(orders, 1, float("inf")) == 0.5
    assert metrics.low_score_rate(orders, 100, 200) is None


def test_logistics_by_state(orders):
    out = metrics.logistics_by_state(orders)
    assert out["customer_state"].tolist() == ["SP", "RJ"]
    assert out["delivered"].tolist() == [2, 2]
    assert out.set_index("customer_state").loc["RJ", "late_rate"] == 0.5
