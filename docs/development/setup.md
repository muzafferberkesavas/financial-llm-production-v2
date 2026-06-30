# Gelistirme Ortami Kurulumu

## Gereksinimler

- Python 3.13+
- Node.js 18+ (frontend'ler icin)
- Git

## Hizli Baslangic

```bash
# Tek komutla tum stack'i baslat (backend + her iki frontend)
./run-local.sh
```

## Manuel Kurulum

### Backend

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e .

# Opsiyonel: FinBERT sentiment
pip install -e ".[nlp]"

# Opsiyonel: Backtest raporlama
pip install -e ".[backtest]"

# Opsiyonel: Gelistirme araclari
pip install -e ".[dev]"
```

### Environment

```bash
cp .env.example .env
# .env dosyasinda API key'leri doldur
```

### Dashboard (Next.js)

```bash
cd dashboard
npm install
npm run dev                     # http://localhost:3000
```

### Vue Frontend

```bash
cd frontend-vue
npm install
npm run dev                     # http://localhost:5173
```

## Yaygin Calistirma Komutlari

```bash
cd backend

# API sunucusu
.venv/bin/python scripts/run_api.py
# veya: uvicorn finllm.api.main:app --reload --port 8000

# BIST sinyalleri (API key gerektirmez, mock LLM)
.venv/bin/python scripts/run_decision_panel.py \
  --market bist \
  --symbols THYAO.IS,GARAN.IS,AKBNK.IS \
  --no-debate --no-macro --export

# Tam pipeline (Claude API key gerektirir)
.venv/bin/python scripts/run_funnel.py \
  --market nasdaq --llm claude --mode pre_market --capital 10000 --quota 12

# Backtest
.venv/bin/python scripts/backtest.py \
  --universe bist --start 2022-01-01 --end 2024-12-31 --costs midas-bist

# Smoke test
.venv/bin/python scripts/smoke_test.py
```

## Yerel URL'ler

| Servis | URL |
|--------|-----|
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Dashboard | http://localhost:3000 |
| Vue Frontend | http://localhost:5173 |
