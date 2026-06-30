# CLAUDE.md - Financial LLM Production v2

AI-powered multi-market swing-trading sinyal sistemi. Hybrid LLM + kantitatif mimari ile NASDAQ ve BIST pazarlari icin 7 asamali karar hunisi uzerinden BUY/SELL sinyalleri uretir.

## Hizli Referans

| Konu | Dokuman |
|------|---------|
| Sistem mimarisi | [docs/architecture/overview.md](docs/architecture/overview.md) |
| Pipeline asamalari | [docs/architecture/pipeline-stages.md](docs/architecture/pipeline-stages.md) |
| Domain modelleri | [docs/architecture/domain-models.md](docs/architecture/domain-models.md) |
| API endpoint'leri | [docs/backend/api-endpoints.md](docs/backend/api-endpoints.md) |
| LLM kullanimi | [docs/backend/llm-usage.md](docs/backend/llm-usage.md) |
| Veritabani | [docs/backend/database.md](docs/backend/database.md) |
| CLI scriptleri | [docs/backend/scripts.md](docs/backend/scripts.md) |
| Frontend'ler | [docs/frontend/overview.md](docs/frontend/overview.md) |
| Ortam degiskenleri | [docs/config/environment.md](docs/config/environment.md) |
| Kurulum | [docs/development/setup.md](docs/development/setup.md) |
| Kodlama konvansiyonlari | [docs/development/conventions.md](docs/development/conventions.md) |
| Test | [docs/development/testing.md](docs/development/testing.md) |
| Production deployment | [docs/deployment/production.md](docs/deployment/production.md) |

## Repo Yapisi (Ozet)

```
backend/src/finllm/     # Ana Python paketi (~130 modul)
  api/                   # FastAPI v2 route'lar
  pipeline/              # 7-asamali orchestrator (stage0→stage5)
  llm/                   # LLM client'lar (claude, mock, debate)
  skills/                # Cached system prompt'lar (markdown)
  signals/               # Sinyal sema + generator
  portfolio/             # Pozisyon yonetimi, cikis, boyutlandirma
  features/              # 50+ teknik indikator
  data/                  # Piyasa verisi (yfinance, Finnhub, FRED, KAP)
  backtest/              # Walk-forward motor
  config/                # Pydantic Settings, universe tanimlari
  storage/               # DuckDB sema + CRUD
backend/scripts/         # CLI giris noktalari
dashboard/               # Next.js 16 + React 19
frontend-vue/            # Vue 3 + Vite + ECharts
fingpt_server/           # Opsiyonel GPU servisi
infra/aws/               # Docker Compose + Caddy
.github/workflows/       # Cron job'lar
```

## Kritik Kurallar

- **pandas < 3.0** kullan (3.x breaking change'ler)
- **pandas-ta-classic** kullan (pandas-ta deprecated)
- BIST ticker'lari `.IS` son eki gerektirir (ornegin `THYAO.IS`)
- `--llm mock` ile API key olmadan calistirilabilir
- LLM maliyet takibi zorunlu — her cagri `cost_usd` döndürmeli
- Pipeline stage'leri `PipelineContext` uzerinden iletisim kurar
- Next.js 16 breaking change'leri icin `node_modules/next/dist/docs/` kontrol et

## Bilinen Gap'ler

1. Dashboard mock veri gosteriyor — gercek API entegrasyonu gerekiyor
2. Test coverage minimal — backtest walk-forward birincil QA
3. Error handling seyrek (bare try/except → 500)
4. FinGPT RAG endpoint POC asmasinda
