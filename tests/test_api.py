import pytest
from fastapi.testclient import TestClient

from api.main import create_app, parse_states
from api.pages import PAGES
from olist_dashboard.data import build_tables
from tests.test_data import raw  # noqa: F401 - fixture des CSV miniatures


@pytest.fixture
def client(raw, tmp_path):  # noqa: F811
    tables = build_tables(raw)
    return TestClient(create_app(load=lambda: tables, web_dist=tmp_path))


def test_meta(client):
    data = client.get("/api/meta").json()
    assert data["states"] == ["RJ", "SP"]
    assert data["default_start"] == "2017-01-01"
    assert data["min_date"] == "2017-03-01"


@pytest.mark.parametrize("page", list(PAGES))
def test_every_page_answers(client, page):
    response = client.get(f"/api/pages/{page}", params={"start": "2017-03-01", "end": "2017-03-31"})
    assert response.status_code == 200
    data = response.json()
    assert data["orders"] == 3
    assert data["period"]["previous"] == {"start": "2017-01-29", "end": "2017-02-28"}
    assert data["kpis"] is not None


def test_overview_content(client):
    data = client.get("/api/pages/overview", params={"states": "sp"}).json()
    assert data["states"] == ["SP"]
    assert data["kpis"]["revenue"] == 33.0  # o1 ; o3 (SP) est annulée
    assert data["monthly"] == [{"month": "2017-03-01", "revenue": 33.0, "orders": 1}]


def test_no_previous_period_before_reliable_range(client):
    data = client.get("/api/pages/overview", params={"start": "2017-01-01", "end": "2017-03-31"}).json()
    assert data["period"]["previous"] is None
    assert data["previous_kpis"] is None


def test_empty_selection_returns_only_header(client):
    data = client.get("/api/pages/overview", params={"start": "2018-01-01", "end": "2018-01-31"}).json()
    assert data["orders"] == 0
    assert "kpis" not in data


@pytest.mark.parametrize(
    ("params", "status"),
    [({"states": "XX"}, 422), ({"start": "2018-02-01", "end": "2018-01-01"}, 422), ({"start": "hier"}, 422)],
)
def test_invalid_filters(client, params, status):
    assert client.get("/api/pages/overview", params=params).status_code == status


def test_unknown_routes(client):
    assert client.get("/api/pages/nope").status_code == 404
    assert client.get("/api/nope").status_code == 404


def test_web_fallback(client, tmp_path):
    assert client.get("/logistique").status_code == 404  # front pas encore compilé
    (tmp_path / "index.html").write_text("<!doctype html><title>Olist</title>")
    (tmp_path / "app.js").write_text("console.log(1)")
    assert "Olist" in client.get("/logistique").text  # navigation côté navigateur
    assert client.get("/app.js").text == "console.log(1)"
    assert "Olist" in client.get("/../pyproject.toml").text  # pas de sortie du dossier


def test_parse_states():
    assert parse_states(" sp, RJ ,,sp", {"SP", "RJ"}) == ("RJ", "SP")
    assert parse_states("", {"SP"}) == ()
