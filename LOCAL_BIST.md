# Lokal Çalıştırma Rehberi (BIST odaklı, tüm stack)

Sistem **lokalde tam çalışır** durumda: backend API + dashboard (Next.js) + frontend-vue (Vue).
Odak BIST/borsa; **FinBERT açılır-kapanır** (opsiyonel), **BIST sembol listesi düzenlenebilir**.
Hiçbir API anahtarı olmadan da UI'da BIST teknik sinyalleri görünür ($0).

---

## Tek komutla başlat
```bash
./run-local.sh        # backend:8000 + dashboard:3000 + frontend-vue:5173 — Ctrl-C durdurur
```
İlk açılışta UI boş kalmasın diye otomatik **$0 anahtarsız BIST seed** üretir.

Adresler:
- **Backend API:** http://localhost:8000  (Swagger: http://localhost:8000/docs)
- **Dashboard (Next.js):** http://localhost:3000  *(port 3000 doluysa Next 3001'e kayar — terminal çıktısına bak)*
  - BIST sinyalleri: **http://localhost:3000/app/signals?market=bist**  (sayfa varsayılan NASDAQ sekmesiyle açılır; BIST sekmesine tıkla)
- **Frontend (Vue panel):** http://localhost:5173  (BIST verisini doğrudan gösterir)

---

## İlk kurulum (bir kez)
```bash
# 1) Backend (Python 3.11)
cd backend
python3.11 -m venv .venv
.venv/bin/python -m pip install -e .          # çekirdek (torch HARİÇ)

# 2) Frontend bağımlılıkları
npm --prefix ../dashboard install
npm --prefix ../frontend-vue install
```
`.env` (repo kökü) ve `dashboard/.env.local` hazır geldi. Anahtar gerekmez.

> **Kurulum notu:** `twopirllc/pandas-ta` (PyPI+GitHub) kaldırıldığı için kurulamıyordu;
> birebir devamı **`pandas-ta-classic`** ile değiştirildi (`pyproject.toml`, `features/technical.py`).

---

## BIST sembol listesi — ekle / çıkar
Düzenlenebilir tek kaynak: **`backend/data/universes/bist100.json`** (101 BIST sembolü).
`[{ "symbol": "THYAO.IS", "name": "...", "sector": "..." }, ...]` formatında.

- **Çıkar:** ilgili satırı sil.  **Ekle:** yeni `{symbol,name,sector}` ekle (sembol `.IS` ekli).
- Bu liste **backtest + walk-forward** evrenini (`--universe bist`) doğrudan besler.
- Sıfırlamak için: `.venv/bin/python scripts/fetch_bist100_universe.py` (yeniden üretir).

UI'daki BIST kartlarını yenilemek (seçtiğin sembollerle):
```bash
cd backend
.venv/bin/python scripts/run_decision_panel.py --market bist \
  --symbols THYAO.IS,GARAN.IS,ASELS.IS,AKBNK.IS,KCHOL.IS --no-debate --no-macro --top-n 5 --export
# veya düzenlediğin tüm listeyi kullan (ilk çalıştırma yavaş olabilir):
.venv/bin/python scripts/run_decision_panel.py --market bist --universe bist --no-debate --no-macro --top-n 12 --export
```
`--export` → `data/out/signals_bist_*.json` yazar; UI bunu otomatik gösterir (sayfayı yenile).

---

## Borsa testleri (anahtarsız)
```bash
cd backend
# Teknik backtest:
.venv/bin/python scripts/backtest.py --universe bist --start 2022-01-01 --end 2024-12-31
# Walk-forward (sağlamlık kapısı):
.venv/bin/python scripts/walkforward.py --universe AKBNK.IS,THYAO.IS,GARAN.IS,EREGL.IS,SISE.IS \
  --start 2022-01-01 --end 2024-06-30 --costs midas-bist
```
> ⚠️ BIST nominal getirileri TRY enflasyonuyla şişer — rakamlar yön göstericidir.

---

## FinBERT (sentiment) — aç / kapat
Varsayılan **kapalı** (`SENTIMENT_PROVIDER=disabled`, nötr) — torch gerekmez.
torch+transformers zaten kurulu; açmak için `.env`:
```
SENTIMENT_PROVIDER=finbert      # lokal FinBERT (Mac MPS/CPU). Kapatmak için: disabled
```
İlk çağrıda model (~400MB) Hugging Face'ten iner. Kurulu değilse: `pip install -e '.[nlp]'`.

---

## LLM tahmini (opsiyonel — gerçek AL/SAT kararı)
Bull/bear debate + nihai karar Claude kullanır. `.env` içine `ANTHROPIC_API_KEY` ekle, sonra:
```bash
cd backend
.venv/bin/python scripts/run_decision_panel.py --market bist --top-n 5 --export   # gerçek LLM sinyalleri
.venv/bin/python -m scripts.generate_signal THYAO.IS                              # tek sembol
```
Dashboard'daki "analiz et" akışı için `dashboard/.env.local` içine de `ANTHROPIC_API_KEY` ekle.

---

## Mimari (lokal)
```
frontend-vue :5173 ──/api proxy──┐
                                 ├──► backend :8000  ──► data/out/signals_bist_*.json
dashboard   :3000 ──BACKEND_API_URL──┘                  (seed veya LLM panel üretir)
```
Tek backend (`finllm.api.main:app`) hem dashboard hem vue'ya hizmet eder
(`/v2/commodities` main'e eklendi). Sinyaller dosya tabanlı JSON'dan okunur.
