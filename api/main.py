"""Application FastAPI : API JSON du dashboard et front React compilé.

Lancement en local : ``uvicorn api.main:app --reload`` (API sur le port 8000).

Réglages par variables d'environnement (voir le Dockerfile pour la production) :

- ``APP_ENV=production`` : masque la documentation interactive de l'API ;
- ``RATE_LIMIT_PER_MINUTE`` : requêtes d'API permises par visiteur et par minute ;
- ``TRUST_PROXY=1`` : lit l'adresse du visiteur dans l'en-tête de l'hébergeur.
"""

import os
import threading
from collections.abc import Callable
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse

from api.pages import PAGES
from api.security import RateLimiter, add_security_headers, env_flag, rate_limit_middleware
from api.serialize import clean
from olist_dashboard.config import RELIABLE_END, RELIABLE_START, ROOT_DIR
from olist_dashboard.data import load_tables
from olist_dashboard.selection import select

WEB_DIST = ROOT_DIR / "web" / "dist"
# Dates acceptées : bien au-delà des données (2016-2018), mais assez bornées pour
# que les calculs de période restent valides.
EARLIEST, LATEST = date(2000, 1, 1), date(2099, 12, 31)
# Calculs en attente au-delà desquels l'API répond « occupée » plutôt que
# d'empiler les requêtes, et attente maximale de chacune.
MAX_PENDING, MAX_WAIT_SECONDS = 8, 20.0


def parse_states(raw: str, known: set[str]) -> tuple[str, ...]:
    """« SP,rj » -> ("RJ", "SP") ; refuse les États inconnus."""
    states = tuple(sorted({s.strip().upper() for s in raw.split(",") if s.strip()}))
    unknown = [s for s in states if s not in known]
    if unknown:
        raise HTTPException(422, f"États inconnus : {', '.join(unknown)}")
    return states


def busy() -> HTTPException:
    return HTTPException(
        503, "Le serveur est très sollicité : réessayez dans quelques secondes.",
        headers={"Retry-After": "5"},
    )


def create_app(
    load: Callable[[], dict[str, pd.DataFrame]] = load_tables,
    web_dist: Path = WEB_DIST,
    production: bool | None = None,
    rate_limit: int | None = None,
    trust_proxy: bool | None = None,
) -> FastAPI:
    if production is None:
        production = os.environ.get("APP_ENV", "").strip().lower() == "production"
    if rate_limit is None:
        rate_limit = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "120"))
    if trust_proxy is None:
        trust_proxy = env_flag("TRUST_PROXY")

    app = FastAPI(
        title="Dashboard Olist",
        docs_url=None if production else "/api/docs",
        redoc_url=None,
        openapi_url=None if production else "/api/openapi.json",
    )
    # Le dernier ajouté s'exécute en premier : la limite de requêtes passe avant
    # tout calcul, et les en-têtes de sécurité couvrent aussi ses refus (429).
    app.add_middleware(GZipMiddleware, minimum_size=1_000)
    if rate_limit > 0:
        app.middleware("http")(rate_limit_middleware(RateLimiter(rate_limit), trust_proxy))
    app.middleware("http")(add_security_headers)

    @lru_cache(maxsize=1)
    def tables() -> dict[str, pd.DataFrame]:
        return load()

    # Un calcul à la fois : pandas ne gagne rien à en mener plusieurs en parallèle,
    # et la mémoire reste sous les 512 Mo des hébergements gratuits.
    # Au-delà de MAX_PENDING calculs en attente, on refuse au lieu d'empiler.
    compute_lock = threading.Lock()
    pending = threading.BoundedSemaphore(MAX_PENDING)

    @lru_cache(maxsize=512)
    def page_data(page: str, start: date, end: date, states: tuple[str, ...]) -> dict[str, Any]:
        if not pending.acquire(blocking=False):
            raise busy()
        try:
            if not compute_lock.acquire(timeout=MAX_WAIT_SECONDS):
                raise busy()
            try:
                return compute(page, start, end, states)
            finally:
                compute_lock.release()
        finally:
            pending.release()

    def compute(page: str, start: date, end: date, states: tuple[str, ...]) -> dict[str, Any]:
        selection = select(tables()["orders"], start, end, list(states))
        header = {
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "previous": (
                    {"start": selection.previous_start, "end": selection.previous_end}
                    if selection.previous_start is not None
                    else None
                ),
            },
            "states": list(states),
            "orders": len(selection.orders),
        }
        if selection.orders.empty:
            return clean(header)
        return clean({**header, **PAGES[page](tables(), selection)})

    @app.get("/api/meta")
    def meta() -> dict[str, Any]:
        """Bornes des dates, période par défaut et liste des États."""
        orders = tables()["orders"]
        return {
            "min_date": orders["purchase_date"].min().strftime("%Y-%m-%d"),
            "max_date": orders["purchase_date"].max().strftime("%Y-%m-%d"),
            "default_start": RELIABLE_START.strftime("%Y-%m-%d"),
            "default_end": RELIABLE_END.strftime("%Y-%m-%d"),
            "states": sorted(orders["customer_state"].dropna().unique().tolist()),
        }

    @app.get("/api/pages/{page}")
    def page(
        page: str,
        start: Annotated[date, Query(description="Premier jour d'achat (AAAA-MM-JJ)")] = RELIABLE_START.date(),
        end: Annotated[date, Query(description="Dernier jour d'achat (AAAA-MM-JJ)")] = RELIABLE_END.date(),
        states: Annotated[
            str, Query(max_length=200, description="États du client, séparés par des virgules")
        ] = "",
    ) -> dict[str, Any]:
        """Données d'une page du dashboard pour la période et les États choisis."""
        if page not in PAGES:
            raise HTTPException(404, f"Page inconnue : {page}. Pages : {', '.join(PAGES)}")
        if not (EARLIEST <= start <= LATEST and EARLIEST <= end <= LATEST):
            raise HTTPException(422, f"Dates acceptées : du {EARLIEST} au {LATEST}.")
        if start > end:
            raise HTTPException(422, "La date de début doit précéder la date de fin.")
        known = set(tables()["orders"]["customer_state"].dropna().unique())
        return page_data(page, start, end, parse_states(states, known))

    @app.get("/api/{path:path}", include_in_schema=False)
    def unknown_api(path: str) -> None:
        raise HTTPException(404, f"Route d'API inconnue : /api/{path}")

    # Front React compilé (``npm run build`` dans web/) : fichiers statiques, et
    # index.html pour toute autre adresse (navigation gérée côté navigateur).
    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def web(path: str) -> FileResponse:
        index = web_dist / "index.html"
        if not index.exists():
            raise HTTPException(
                404, "Front non compilé : lancez « npm run build » dans web/, ou utilisez "
                "« npm run dev » pendant le développement."
            )
        file = (web_dist / path).resolve()
        if path and file.is_file() and file.is_relative_to(web_dist.resolve()):
            return FileResponse(file)
        if path.startswith("assets/"):
            # Fichier compilé introuvable : pas de page d'accueil mise en cache à sa place.
            raise HTTPException(404, "Fichier introuvable.")
        return FileResponse(index)

    return app


app = create_app()
