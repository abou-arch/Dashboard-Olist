"""Protections HTTP de l'application publique.

- En-têtes de sécurité sur toutes les réponses (CSP, HSTS, anti-iframe…).
- Limite de requêtes par visiteur sur l'API, contre les abus et les robots.
- Mise en cache adaptée : fichiers du site compilé (nom avec empreinte) gardés
  un an par le navigateur, page d'accueil et données toujours revalidées.
"""

import os
import threading
import time
from collections import defaultdict, deque

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Le site ne charge que ses propres fichiers (police et scripts compris) : tout le
# reste est refusé. Les styles en ligne sont nécessaires aux info-bulles d'ECharts,
# et Vite intègre les plus petits fichiers de police dans le CSS (« data: »).
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "font-src 'self' data:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    # HTTPS obligatoire pendant un an (ignoré par les navigateurs en HTTP local).
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}

# La documentation interactive de l'API charge Swagger depuis un CDN : elle n'est
# servie qu'en développement, et sans politique de contenu stricte.
DOCS_PATHS = ("/api/docs", "/api/openapi.json", "/api/docs/oauth2-redirect")


def cache_control(path: str) -> str:
    if path.startswith("/assets/"):
        return "public, max-age=31536000, immutable"
    return "no-cache"


async def add_security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        if name == "Content-Security-Policy" and request.url.path.startswith(DOCS_PATHS):
            continue
        response.headers.setdefault(name, value)
    response.headers.setdefault("Cache-Control", cache_control(request.url.path))
    return response


def client_ip(request: Request, trust_proxy: bool) -> str:
    """Adresse du visiteur ; derrière l'hébergeur, elle arrive dans X-Forwarded-For.

    Cette adresse n'est pas une preuve d'identité (un client peut la falsifier) :
    elle sert seulement à répartir la limite de requêtes. La protection de fond
    reste le calcul unique et la file d'attente bornée de l'API.
    """
    if trust_proxy:
        forwarded = request.headers.get("x-forwarded-for", "")
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "inconnu"


class RateLimiter:
    """Au plus ``limit`` requêtes par fenêtre glissante de ``window`` secondes et par clé."""

    def __init__(self, limit: int, window: float = 60.0, clock=time.monotonic):
        self.limit = limit
        self.window = window
        self.clock = clock
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, key: str) -> float | None:
        """None si la requête passe, sinon le nombre de secondes avant de réessayer."""
        now = self.clock()
        with self.lock:
            hits = self.hits[key]
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return hits[0] + self.window - now
            hits.append(now)
            # Ménage : on oublie les visiteurs inactifs pour borner la mémoire.
            if len(self.hits) > 10_000:
                for stale in [k for k, h in self.hits.items() if not h or h[-1] <= now - self.window]:
                    del self.hits[stale]
            return None


def rate_limit_middleware(limiter: RateLimiter, trust_proxy: bool):
    async def middleware(request: Request, call_next) -> Response:
        if request.url.path.startswith("/api/"):
            retry_after = limiter.check(client_ip(request, trust_proxy))
            if retry_after is not None:
                return JSONResponse(
                    {"detail": "Trop de requêtes : réessayez dans quelques secondes."},
                    status_code=429,
                    headers={"Retry-After": str(max(1, round(retry_after)))},
                )
        return await call_next(request)

    return middleware


def env_flag(name: str, default: bool = False) -> bool:
    return os.environ.get(name, "1" if default else "0").strip().lower() in {"1", "true", "yes", "oui"}
