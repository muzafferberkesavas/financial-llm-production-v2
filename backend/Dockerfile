# Production Dockerfile — FinLLM backend
#
# Build:
#   docker build -t finllm-backend ./backend
# Run locally:
#   docker run --env-file ../.env -p 8000:8000 finllm-backend

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# System deps — bcrypt, lxml, psycopg gibi paketler için
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps first (Docker cache layer)
COPY pyproject.toml /app/
RUN pip install -e . || \
    (pip install \
        "pandas>=2.2" \
        "numpy>=1.26,<2.3" \
        "yfinance>=0.2.50" \
        "finnhub-python>=2.4" \
        "httpx>=0.27" \
        "tenacity>=9.0" \
        "pandas-ta>=0.3.14b" \
        "scikit-learn>=1.5" \
        "anthropic>=0.40" \
        "fastapi>=0.115" \
        "uvicorn[standard]>=0.32" \
        "pydantic>=2.9" \
        "pydantic-settings>=2.5" \
        "sqlalchemy>=2.0" \
        "psycopg[binary]>=3.3" \
        "duckdb-engine>=0.17" \
        "alembic>=1.18" \
        "defusedxml>=0.7" \
        "aiogram>=3.28" \
        "python-multipart>=0.0.7")

# App code
COPY src /app/src
COPY scripts /app/scripts

# Skill markdown'ları
RUN ls -la /app/src/finllm/skills

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/v2/health || exit 1

EXPOSE 8000

# Default — API; cron runner için ENV ile override:
#   docker run -e MODE=worker → worker entrypoint
ENV MODE=api

CMD ["sh", "-c", "if [ \"$MODE\" = worker ]; then python /app/scripts/cron_worker.py; else uvicorn finllm.api.main:app --host 0.0.0.0 --port 8000; fi"]
