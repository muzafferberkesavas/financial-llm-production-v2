# Production Dockerfile — FinLLM backend
#
# Build:
#   docker build -t finllm-backend ./backend
# Run locally:
#   docker run --env-file ../.env -p 8000:8000 finllm-backend

FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Sistem bağımlılıkları: lxml, psycopg ve bcrypt gibi paketler için
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# pyproject.toml'ı önce kopyala — bağımlılık katmanı cache için
COPY pyproject.toml /app/

# Editable install setuptools'tan src/ ister; gerçek kod COPY edilmeden
# önce minimal bir kabuk oluşturup deps katmanını cache'liyoruz.
RUN mkdir -p /app/src/finllm && touch /app/src/finllm/__init__.py \
    && pip install -e .

# Gerçek uygulama kodu (önceki mock src'i override eder)
COPY src /app/src
COPY scripts /app/scripts

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/v2/health || exit 1

EXPOSE 8000

# Default — API; cron runner için ENV ile override:
#   docker run -e MODE=worker
ENV MODE=api

CMD ["sh", "-c", "if [ \"$MODE\" = worker ]; then python /app/scripts/cron_worker.py; else uvicorn finllm.api.main:app --host 0.0.0.0 --port 8000; fi"]
