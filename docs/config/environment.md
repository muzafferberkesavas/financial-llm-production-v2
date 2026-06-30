# Ortam Degiskenleri ve Yapilandirma

Tum yapilandirma `.env` dosyasi uzerinden okunur. Pydantic Settings: `backend/src/finllm/config/settings.py`
Sablonlar: `.env.example`

## Zorunlu API Key'ler (tam islem icin)

| Degisken | Amac |
|----------|------|
| `ANTHROPIC_API_KEY` | Claude LLM (birincil motor) |
| `FINNHUB_API_KEY` | Piyasa verisi + haberler |
| `FRED_API_KEY` | Makro ekonomik veri (CPI, Fed faizi, issizlik) |

## Opsiyonel API Key'ler

| Degisken | Amac |
|----------|------|
| `OPENAI_API_KEY` | Multi-LLM ensemble |
| `GOOGLE_API_KEY` | Multi-LLM ensemble |
| `AI_GATEWAY_API_KEY` | AI gateway |
| `ALPHA_VANTAGE_API_KEY` | Alternatif piyasa verisi |
| `NEWSAPI_KEY` | Haber API |
| `POLYGON_API_KEY` | Polygon piyasa verisi |
| `TCMB_API_KEY` | Turkiye Cumhuriyet Merkez Bankasi |
| `TELEGRAM_BOT_TOKEN` | Telegram sinyal iletimi |
| `TELEGRAM_CHANNEL_NASDAQ` | NASDAQ kanal ID |
| `TELEGRAM_CHANNEL_BIST` | BIST kanal ID |
| `TELEGRAM_ADMIN_IDS` | Admin kullanici ID'leri |

## Runtime Ayarlari

| Degisken | Varsayilan | Aciklama |
|----------|-----------|----------|
| `DATABASE_URL` | `duckdb:///./backend/data/finllm.duckdb` | Veritabani baglantisi |
| `PORTFOLIO_INITIAL_CAPITAL_USD` | `10000` | Baslangic sermayesi |
| `SENTIMENT_PROVIDER` | `disabled` | Sentiment motoru: `disabled`, `finbert`, `fingpt` |
| `LOG_LEVEL` | `INFO` | Log seviyesi |
| `ENV` | `development` | Ortam: `development`, `production` |

## Notlar

- `--llm mock` ile calistirma hicbir API key gerektirmez (deterministik test)
- `SENTIMENT_PROVIDER=finbert` icin `pip install -e ".[nlp]"` (torch + transformers) gerekir
- BIST ticker'lari `.IS` son eki kullanir (ornegin `THYAO.IS`)
- Universe dosyalari: `backend/data/universes/bist100.json` (101 sembol)
