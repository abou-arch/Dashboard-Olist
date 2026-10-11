import pandas as pd
import pytest

from olist_dashboard import metrics


@pytest.fixture
def orders():
    return pd.DataFrame(
        {
            "order_id": list("abcdef"),
            "order_status": ["delivered"] * 4 + ["canceled", "delivered"],
            "purchase_date": pd.to_datetime(
                ["2018-01-05", "2018-01-20", "2018-02-01", "2018-02-02", "2018-02-03", "2018-02-04"]
            ),
            # c : deux avis (4 et 5) -> 4,5 -> arrondi à 5 étoiles ; f : pas d'avis.
            "review_score": [5.0, 1.0, 4.5, 2.0, 1.0, None],
            "has_comment": pd.array([False, True, False, True, True, pd.NA], dtype="boolean"),
            "delay_days": [-5.0, 3.0, 0.0, -1.0, None, -2.0],
            "n_items": [1, 2, 1, 3, 0, 1],
        }
    )


@pytest.fixture
def items():
    return pd.DataFrame(
        {
            "order_id": ["a", "b", "b", "c", "d", "d"],
            "category": ["Toys", "Toys", "Toys", "Auto", "Auto", "Toys"],
        }
    )


def test_reviewed_rounds_scores(orders):
    rated = metrics.reviewed(orders)
    assert rated["order_id"].tolist() == list("abcde")
    assert rated["stars"].tolist() == [5, 1, 5, 2, 1]


def test_compute_satisfaction_kpis(orders):
    kpis = metrics.compute_satisfaction_kpis(orders)
    assert kpis.reviewed == 5
    assert kpis.response_rate == pytest.approx(5 / 6)
    assert kpis.average_review == pytest.approx(2.7)
    assert kpis.satisfied_share == pytest.approx(0.4)
    assert kpis.dissatisfied_share == pytest.approx(0.6)
    assert kpis.comment_rate == pytest.approx(0.6)
    assert kpis.dissatisfied_comment_rate == 1.0


def test_score_distribution(orders):
    out = metrics.score_distribution(orders)
    assert out["stars"].tolist() == [5, 4, 3, 2, 1]
    assert out["orders"].tolist() == [2, 0, 0, 1, 2]
    assert out["share"].sum() == pytest.approx(1.0)
    assert out["label"].iloc[0] == "5 ★"


def test_monthly_satisfaction(orders):
    out = metrics.monthly_satisfaction(orders)
    assert out["reviewed"].tolist() == [2, 3]
    assert out["review_score"].tolist() == [3.0, pytest.approx(7.5 / 3)]


def test_review_by_delivery(orders):
    out = metrics.review_by_delivery(orders).set_index("group")
    assert out.loc["Livrée à temps", "orders"] == 3
    assert out.loc["Livrée à temps", "review_score"] == pytest.approx(11.5 / 3)
    assert out.loc["Livrée en retard", "review_score"] == 1.0
    assert out.loc["Non livrée", "dissatisfied_share"] == 1.0


def test_review_by_items(orders):
    out = metrics.review_by_items(orders).set_index("group")
    assert out["orders"].tolist() == [2, 1, 1]
    assert out.loc["1 article", "review_score"] == pytest.approx(4.75)


def test_review_by_category_counts_each_order_once_per_category(orders, items):
    out = metrics.review_by_category(orders, items).set_index("category")
    assert out.loc["Toys", "orders"] == 3  # a, b (deux articles), d
    assert out.loc["Toys", "review_score"] == pytest.approx(8 / 3)
    assert out.loc["Auto", "review_score"] == pytest.approx(3.25)
    assert out.index.tolist() == ["Toys", "Auto"]  # de la moins bien à la mieux notée


def test_min_reviews_for_ranking():
    assert metrics.min_reviews_for_ranking(1_000) == 20
    assert metrics.min_reviews_for_ranking(100_000) == 300
