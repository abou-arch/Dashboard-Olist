# Image de production : front React compilé + API FastAPI, sur un seul port.

# 1. Compilation du front (les scripts d'installation des paquets ne sont pas exécutés)
FROM node:25-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY web/ ./
RUN npm run build

# 2. API Python, qui sert aussi le front compilé
FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Limitent la mémoire gardée par les allocateurs (≈ 320 Mo au lieu de 450).
    MALLOC_ARENA_MAX=2 \
    ARROW_DEFAULT_MEMORY_POOL=system \
    # Sécurité (voir api/main.py) : pas de documentation d'API publique, et
    # adresse du visiteur lue dans l'en-tête ajouté par l'hébergeur.
    APP_ENV=production \
    TRUST_PROXY=1 \
    RATE_LIMIT_PER_MINUTE=120 \
    PORT=8000
COPY requirements-api.txt ./
RUN pip install -r requirements-api.txt
# Le code et les données appartiennent à root : l'utilisateur qui fait tourner
# l'application peut les lire, pas les modifier.
COPY olist_dashboard/ olist_dashboard/
COPY api/ api/
COPY data/processed/ data/processed/
COPY --from=web /web/dist web/dist
RUN useradd --system --no-create-home --shell /usr/sbin/nologin app
USER app
EXPOSE 8000
# --no-server-header : ne révèle pas le serveur utilisé ;
# --limit-concurrency : au-delà de 50 connexions simultanées, réponse 503 immédiate.
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --no-server-header --limit-concurrency 50"]
