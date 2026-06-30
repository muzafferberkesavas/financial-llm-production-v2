# Production Deployment

## Docker (AWS EC2)

### Yapilandirma Dosyalari

- `infra/aws/docker-compose.yml` — Servis tanimlari
- `infra/aws/Caddyfile` — Reverse proxy (HTTPS, Let's Encrypt)
- `backend/Dockerfile` — Backend image

### Servisler

```yaml
services:
  postgres:        # PostgreSQL 16 (dahili, sadece API erisir)
  api:             # FastAPI (uvicorn) — port 8000
  telegram-dm:     # Telegram bot sidecar
  caddy:           # Reverse proxy — port 80/443 (HTTPS)
```

### Calistirma

```bash
cd infra/aws
cp .env.example .env     # Tum secret'lari doldur
docker compose up -d --build
```

### Dockerfile Giris Noktasi

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get install build-essential libpq-dev curl
COPY pyproject.toml .
RUN pip install -e .
COPY src /app/src
EXPOSE 8000
CMD ["sh", "-c", "if [ \"$MODE\" = worker ]; then python /app/scripts/cron_worker.py; else uvicorn finllm.api.main:app --host 0.0.0.0 --port 8000; fi"]
```

`MODE=worker` ile cron worker olarak, yoksa API sunucusu olarak calisir.

## GitHub Actions CI/CD

Workflow dosyalari: `.github/workflows/`

### Cron Isler

| Workflow | Zamanlama | Piyasa | Sermaye | Kota |
|----------|----------|--------|---------|------|
| `cron_nasdaq.yml` | Hafta ici 09:00 UTC (04:00 ET) | NASDAQ | $10,000 | 12 |
| `cron_bist.yml` | Hafta ici 06:30 UTC (09:30 TR) | BIST | $50,000 | 10 |

### Is Akisi

1. Python 3.12 + bagimliliklari kur
2. `scripts/run_funnel.py` calistir (piyasa, LLM backend, sermaye, kota)
3. Sinyal JSON artifact'ini yukle
4. Basarisizlikta Telegram bildirim gonder

### Manuel Tetikleme

Her iki workflow da `workflow_dispatch` destekler (LLM backend secimi ile).

## Outcomes Guncelleme

`cron_outcomes.yml` — Portfolio sonuclarini gunceller ve Platt modelini kalibre eder.

## Izleme

- `/v2/health` endpoint'i ozellik durumlarını raporlar (Claude, Finnhub, Telegram)
- Her pipeline calistirmasi maliyet ve sure takibi yapar
- Telegram basarisizlik bildirimleri
