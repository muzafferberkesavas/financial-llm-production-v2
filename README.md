# Financial LLM Production

Hibrit **LLM + quant** swing-trading sinyal sistemi. ABD hisseleri için fiyat/teknik göstergeler + haber sentiment'i + çoklu LLM ensemble voting ile günlük AL/SAT sinyalleri üretir, DuckDB'de portföy tutar, Next.js dashboard'dan gösterir.

---

## Mimari (3 servis)

```
┌─────────────────────┐      ┌──────────────────────┐      ┌────────────────────┐
│  dashboard/         │ ───► │  backend/            │ ───► │  fingpt_server/    │
│  Next.js 16         │ HTTP │  FastAPI + DuckDB    │ HTTP │  FastAPI + PyTorch │
│  React 19, AI SDK   │      │  Sinyal üretimi      │      │  FinBERT + FinGPT  │
│  Sinyalleri gösterir│      │  Portföy yönetimi    │      │  RAG (SEC filings) │
└─────────────────────┘      └──────────────────────┘      └────────────────────┘
       (localhost:3000)            (localhost:8000)              (AWS EC2 / GPU)
```

- **backend** = ana beyin. Veri çek → teknik göstergeleri hesapla → sentiment skoru al → Claude+OpenAI ensemble → sinyal kaydet.
- **fingpt_server** = ağır ML işleri (FinBERT/FinGPT/RAG). Backend ona HTTP üzerinden istek atar. AWS GPU instance'ında çalışmak için tasarlandı, opsiyonel.
- **dashboard** = sadece görüntü katmanı. Backend'den sinyalleri çekip kart kart gösterir + Claude streaming ile analiz.

---

## Hızlı Başlangıç

### 1. Clone & env
```bash
git clone https://github.com/muzafferberkesavas/financial-llm-production.git
cd financial-llm-production
cp .env.example .env
# .env'i aç, en azından ANTHROPIC_API_KEY ve FINNHUB_API_KEY doldur
```

### 2. Backend (terminal 1)
```bash
cd backend
uv venv && source .venv/bin/activate     # veya: python3.11 -m venv .venv
uv pip install -e .                       # veya: pip install -e .
uvicorn finllm.api.server:app --reload --port 8000
# → http://localhost:8000/docs (Swagger)
```

### 3. Dashboard (terminal 2)
```bash
cd dashboard
cp ../.env.example .env.local             # ANTHROPIC_API_KEY lazım
npm install
npm run dev
# → http://localhost:3000
```

### 4. fingpt_server (opsiyonel, GPU lazım)
```bash
cd fingpt_server
# AWS EC2'de:  bash setup_aws.sh
# Lokalde (CPU fallback):  pip install -r requirements.txt && uvicorn app.main:app --port 8001
```

### 5. Smoke test
```bash
cd backend && python scripts/smoke_test.py
```

---

## Kod Haritası (Claude Code için)

Bir görev gelince hangi dosyaya bakacaksın:

| Görev | Bakılacak dosya |
|---|---|
| Yeni endpoint ekle | `backend/src/finllm/api/server.py` |
| Sinyal mantığını değiştir | `backend/src/finllm/signals/generator.py` |
| Yeni teknik gösterge ekle | `backend/src/finllm/features/technical.py` |
| LLM prompt'larını değiştir | `backend/src/finllm/signals/multi_llm_voter.py` |
| Portföy/pozisyon mantığı | `backend/src/finllm/portfolio/` |
| Veri kaynağı (yfinance, finnhub) | `backend/src/finllm/data/` |
| Dashboard ana sayfa | `dashboard/src/app/page.tsx` |
| Sinyal kartı UI | `dashboard/src/components/signal-card.tsx` |
| Dashboard → backend bağlantısı | `dashboard/src/app/api/signals/route.ts` |
| Claude streaming analiz | `dashboard/src/app/api/analyze/route.ts` |
| FinBERT sentiment endpoint'i | `fingpt_server/app/sentiment.py` |
| FinGPT forecaster | `fingpt_server/app/forecaster.py` |
| SEC RAG indeksi | `fingpt_server/app/rag_index.py` |
| CLI: günlük portföy refresh | `backend/scripts/daily_refresh.py` |
| CLI: tek sembol için sinyal | `backend/scripts/generate_signal.py` |

---

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, DuckDB, pandas, pandas-ta, transformers, torch, anthropic, openai, yfinance, finnhub
- **FinGPT Server:** FastAPI, PyTorch, transformers, peft (LoRA), FAISS, langchain, sec-edgar-downloader
- **Dashboard:** Next.js 16, React 19, Tailwind v4, Vercel AI SDK 6, Zod, Recharts, lucide-react
- **Storage:** DuckDB (yerel, `backend/data/finllm.duckdb`)

---

## Durum: Yapılanlar / Eksikler

### ✅ Yapıldı
- Backend pipeline tam çalışıyor: veri → 50+ teknik gösterge → sentiment → multi-LLM ensemble → sinyal
- 8 API endpoint hazır (`/health`, `/signals/latest`, `/signals/generate`, `/portfolio`, vb.)
- DuckDB portfolio repository + position sizing + exit stratejileri
- FinGPT server: 3 endpoint (sentiment, forecast, RAG), AWS setup script'i
- Dashboard: sinyal grid + Claude streaming analiz endpoint'i
- `.env.example` 10 entegrasyon için şablon

### ❌ Eksik (öncelik sırası)
1. **Dashboard hâlâ mock data gösteriyor** — `dashboard/src/lib/mock-signals.ts` yerine `/api/signals` gerçekten çağrılacak (`dashboard/src/app/page.tsx`)
2. **Portfolio sayfası yok** — backend `/portfolio*` endpoint'leri hazır, frontend yok
3. **Test suite boş** — `backend/tests/` klasörü mevcut ama içi boş
4. **Backend hata yönetimi zayıf** — try/except yok, exception → 500
5. **CI/CD yok** — GitHub Actions kurulmalı
6. **FinGPT `/rag/query` PoC** — gerçek SEC filings ingestion test edilmedi
7. **Monitoring/alerting yok**

---

## Önemli Notlar

- **`.env` asla commit edilmez.** `.gitignore`'da. Yeni API key gelirse `.env.example`'a anahtar adını ekle, değeri boş bırak.
- **DuckDB dosyası da gitignored** (`backend/data/finllm.duckdb`). Lokal state.
- **fingpt_server opsiyonel.** Backend sentiment'i kendi içinde de hesaplayabiliyor (FinBERT direkt). GPU yoksa fingpt_server'ı atla.
- **`pyproject.toml` optional `qlib` extra'sı var** ama henüz kullanılmıyor.

---

## Claude Code ile Çalışırken

Tipik bir görev için akış:
1. Yukarıdaki **Kod Haritası**'ndan ilgili dosyayı bul
2. `backend/scripts/smoke_test.py` ile hızlı sanity check
3. Backend değişikliği yaptıysan: `uvicorn finllm.api.server:app --reload` zaten reload eder
4. Dashboard değişikliği yaptıysan: `npm run dev` zaten reload eder
5. Yeni dependency: `backend/pyproject.toml` veya `dashboard/package.json`'a ekle, sonra reinstall

**Önce oku:** `backend/AGENTS.md` ve `dashboard/CLAUDE.md` (varsa o servise özel notlar).
