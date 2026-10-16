import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.security import CONTENT_SECURITY_POLICY, RateLimiter
from olist_dashboard.data import build_tables
from tests.test_data import raw  # noqa: F401 - fixture des CSV miniatures


@pytest.fixture
def web_dist(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app-123.js").write_text("console.log(1)")
    (tmp_path / "index.html").write_text("<!doctype html><title>Olist</title>")
    return tmp_path


@pytest.fixture
def make_client(raw, web_dist):  # noqa: F811
    tables = build_tables(raw)

    def make(**options):
        return TestClient(create_app(load=lambda: tables, web_dist=web_dist, **options))

    return make


def test_security_headers_on_pages_api_and_errors(make_client):
    client = make_client(production=True)
    for url in ("/", "/ventes", "/api/meta", "/api/pages/inconnue"):
        headers = client.get(url).headers
        assert headers["content-security-policy"] == CONTENT_SECURITY_POLICY
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["x-frame-options"] == "DENY"
        assert "max-age=" in headers["strict-transport-security"]


def test_cache_control(make_client):
    client = make_client()
    assert client.get("/assets/app-123.js").headers["cache-control"].endswith("immutable")
    assert client.get("/").headers["cache-control"] == "no-cache"
    assert client.get("/api/meta").headers["cache-control"] == "no-cache"


def test_missing_asset_is_not_replaced_by_index(make_client):
    assert make_client().get("/assets/absent.js").status_code == 404


def test_docs_hidden_in_production(make_client):
    production = make_client(production=True)
    assert production.get("/api/docs").status_code == 404
    assert production.get("/api/openapi.json").status_code == 404
    development = make_client(production=False)
    assert development.get("/api/openapi.json").status_code == 200
    assert "content-security-policy" not in development.get("/api/docs").headers


def test_rate_limit_on_api_only(make_client):
    client = make_client(rate_limit=3)
    assert [client.get("/api/meta").status_code for _ in range(4)] == [200, 200, 200, 429]
    refused = client.get("/api/meta")
    assert int(refused.headers["retry-after"]) >= 1
    assert refused.headers["x-frame-options"] == "DENY"
    assert client.get("/").status_code == 200  # le site lui-même reste servi


def test_rate_limit_per_forwarded_ip_behind_proxy(make_client):
    client = make_client(rate_limit=1, trust_proxy=True)
    assert client.get("/api/meta", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    assert client.get("/api/meta", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 429
    assert client.get("/api/meta", headers={"X-Forwarded-For": "2.2.2.2, 10.0.0.1"}).status_code == 200


def test_rate_limiter_window_slides():
    now = [0.0]
    limiter = RateLimiter(2, window=60, clock=lambda: now[0])
    assert limiter.check("a") is None
    assert limiter.check("a") is None
    assert limiter.check("a") == pytest.approx(60)
    assert limiter.check("b") is None  # chaque visiteur a son propre quota
    now[0] = 60.5
    assert limiter.check("a") is None


@pytest.mark.parametrize(
    "params",
    [
        {"start": "0001-01-01"},
        {"end": "9999-12-31"},
        {"states": "SP," * 100},
        {"start": "pas-une-date"},
    ],
)
def test_rejects_out_of_range_or_oversized_parameters(make_client, params):
    assert make_client().get("/api/pages/dashboard", params=params).status_code == 422


def test_busy_server_answers_503(make_client, monkeypatch):
    monkeypatch.setattr("api.main.MAX_PENDING", 0)  # file d'attente déjà pleine
    response = make_client().get("/api/pages/dashboard")
    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
