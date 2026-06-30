# Kodlama Konvansiyonlari ve Tech Stack

## Tech Stack

### Backend
- **Python 3.13+**
- **FastAPI** — Web framework
- **Pydantic 2.9+** — Veri dogrulama ve serialization
- **pandas 2.2** — Veri isleme (3.x KULLANILMAZ, breaking API degisiklikleri)
- **numpy 2.x** (2.0-2.3)
- **pandas-ta-classic** — Teknik indikatörler (pandas-ta'dan migrate edildi)
- **DuckDB** — Lokal veritabani
- **PostgreSQL** — Production veritabani
- **anthropic SDK** — Claude API client
- **yfinance** — Piyasa verisi
- **aiogram 3.13+** — Telegram bot
- **SQLAlchemy** — ORM (DuckDB/PostgreSQL)

### Dashboard
- **Next.js 16**, **React 19**
- **Tailwind CSS 4**
- **Recharts** — Grafikler
- **Vercel AI SDK** — Claude streaming
- **Zod** — Sema dogrulama

### Vue Frontend
- **Vue 3.5**, **Vite 6**
- **Pinia 2** — State management
- **ECharts 6** — Gelismis grafikler
- **Tailwind CSS 4**

## Python Konvansiyonlari

- **Isimlendirme:** `snake_case` (fonksiyonlar, degiskenler, moduller)
- **Type hints:** Her yerde kullanilir
- **Veri kontratlari:** Pydantic `BaseModel` ile tanimlanir
- **Async:** FastAPI route'lar ve LLM cagrilari icin; veri isleme sync
- **Import sirasi:** stdlib → third-party → local (`finllm.*`)

## Pipeline Konvansiyonlari

- Her stage bagimsiz bir modul (`stage0_ingest.py`, `stage1_filter.py`, vb.)
- Tum stage'ler `PipelineContext` paylasilir
- Stage sonuclari context'e yazilir, sonraki stage oradan okur

## Market Adaptörleri

- `markets/` altinda piyasa bazli soyutlama
- BIST ticker'lari `.IS` son eki kullanir (ornegin `THYAO.IS`, `GARAN.IS`)
- Her adaptör ticaret saatleri, ticker formatı, maliyet modeli saglar

## Onemli Bagimlilik Notlari

- **pandas < 3.0** — 3.x breaking change'ler nedeniyle kilitli
- **pandas-ta → pandas-ta-classic** — Eski paket deprecated, yeni paketle degistirildi
- **numpy 2.0-2.3** — Ust sinir kilitli
