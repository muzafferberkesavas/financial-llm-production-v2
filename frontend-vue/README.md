# FinLLM Frontend (Vue 3)

Modern karar paneli — Vue 3 + Vite + TypeScript + Tailwind 4 + Pinia + Vue Router.
Backend `panel_server`'ı tüketir (framework-bağımsız JSON).

## Çalıştır

```bash
# 1) Backend (panel verisi + API)
cd ../backend
../.venv/bin/python ../backend/scripts/run_decision_panel.py --top-n 4 --export   # panel JSON üret
../.venv/bin/python -m uvicorn finllm.api.panel_server:app --port 8000            # API

# 2) Frontend
npm install
npm run dev        # http://localhost:5173 (dev proxy: /api → :8000)
```

Prod için: `VITE_API_URL=https://api.örnek.com npm run build`.

## Yapı
- `src/types.ts` — backend kontratı (ExtendedSignal, PortfolioResponse)
- `src/lib/api.ts` — `/v2/signals/latest`, `/v2/portfolio`
- `src/stores/panel.ts` — Pinia (market, signals, portfolio, load)
- `src/views/` — Sinyaller, Portföy
- `src/components/SignalCard.vue` — sinyal kartı (AL/IZLE/SAT, güven, bull/bear, tahsis)
