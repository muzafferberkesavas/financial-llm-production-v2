# Sistem Mimarisi

## Genel Bakis

AI-powered multi-market swing-trading sinyal sistemi. Hybrid LLM + kantitatif mimari ile NASDAQ ve BIST pazarlari icin BUY/SELL sinyalleri uretir.

## 7-Katmanli Pipeline

```
Data Ingest → News Agenda → Hard Filters → Setup Scoring → Feature Matrix
    → LLM Screening (Haiku) → Deep Analysis (Opus) → Bull/Bear Debate
    → Backtest Gate → Portfolio Construction → Signal Export
```

## Temel Tasarim Kararlari

- **Claude model tiering:** Haiku 4.5 screening (~$0.001/ticker), Opus deep analysis (~$0.15/ticker), Sonnet 4.6 debate judge
- **DuckDB** lokal gelistirme, **PostgreSQL** production
- **Walk-forward backtest** sinyal yayinlanmadan once kalite kapisi olarak kullanilir
- **Prompt caching** cached system prompt'larda %90 maliyet azaltma
- **Tool-use structured output** LLM yanıtlarında JSON parsing yerine tool çağrısı

## Repository Yapisi

```
├── backend/                 # Python 3.13+ FastAPI backend (ana motor)
│   ├── src/finllm/          # Ana paket (~130 modul)
│   │   ├── api/             # FastAPI v2 route'lar (signals, portfolio, websocket)
│   │   ├── pipeline/        # 7-asamali orchestrator (stage0 → stage5)
│   │   ├── llm/             # LLM client'lar (claude.py, mock.py, debate.py)
│   │   ├── skills/          # Role bazli cached system prompt'lar
│   │   ├── signals/         # Sinyal sema (Pydantic) + generator
│   │   ├── portfolio/       # Pozisyon yonetimi, cikis, boyutlandirma (Kelly/Platt)
│   │   ├── features/        # 50+ teknik indikatör (pandas-ta-classic)
│   │   ├── data/            # Piyasa verisi (yfinance, Finnhub, FRED, KAP)
│   │   ├── backtest/        # Walk-forward motor, metrikler, maliyet modelleri
│   │   ├── calibration/     # Platt scaling, Kelly criterion, reliability
│   │   ├── sentiment/       # FinBERT (opsiyonel), FinGPT client
│   │   ├── ensemble/        # Multi-LLM oylama (Claude birincil)
│   │   ├── storage/         # DuckDB sema + CRUD
│   │   ├── config/          # Pydantic Settings (.env), universe tanimlari
│   │   └── markets/         # Piyasa adaptörleri (NASDAQ, BIST, commodities)
│   ├── scripts/             # CLI giris noktalari (run_funnel, backtest, vb.)
│   ├── data/                # Runtime veri (DuckDB, sinyal ciktilari, cache)
│   └── tests/               # Test dizini
├── dashboard/               # Next.js 16 + React 19 frontend
├── frontend-vue/            # Vue 3 + Vite + ECharts alternatif frontend
├── fingpt_server/           # Opsiyonel GPU servisi (FinBERT/FinGPT/RAG)
├── infra/aws/               # Docker Compose + Caddy deployment
└── .github/workflows/       # Cron job'lar (NASDAQ 09:00 UTC, BIST 06:30 UTC)
```

## Anahtar Giris Noktalari

| Dosya | Amac |
|-------|------|
| `backend/src/finllm/api/main.py` | FastAPI v2 uygulama fabrikasi |
| `backend/src/finllm/pipeline/orchestrator.py` | `run_pipeline()` - ana pipeline girisi |
| `backend/scripts/run_funnel.py` | CLI pipeline calistirici |
| `backend/scripts/run_decision_panel.py` | Top-N tartisma + export |
| `backend/scripts/daily_refresh.py` | Portfolio yenileme is akisi |
| `backend/scripts/backtest.py` | Backtesting calistirici |
