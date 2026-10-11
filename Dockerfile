# Image de production : front React compilé + API FastAPI, sur un seul port.

# 1. Compilation du front
FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# 2. API Python, qui sert aussi le front compilé
FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # Limitent la mémoire gardée par les allocateurs (≈ 320 Mo au lieu de 450).
    MALLOC_ARENA_MAX=2 \
    ARROW_DEFAULT_MEMORY_POOL=system \
    PORT=8000
COPY requirements-api.txt ./
RUN pip install -r requirements-api.txt
COPY olist_dashboard/ olist_dashboard/
COPY api/ api/
COPY data/processed/ data/processed/
COPY --from=web /web/dist web/dist
RUN useradd --create-home app
USER app
EXPOSE 8000
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
