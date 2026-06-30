# API Endpoint Referansi

FastAPI v2 uygulamasi: `backend/src/finllm/api/main.py`
Route dosyaları: `backend/src/finllm/api/routes/`

## v2 Endpoints

| Method | Path | Dosya | Amac |
|--------|------|-------|------|
| GET | `/v2/health` | `main.py` | Sistem durumu + ozellik bayraklari (Claude, Finnhub, Telegram) |
| GET | `/v2/signals/latest` | `routes/signals.py` | Son calistirma sinyalleri (dosya veya DB) |
| GET | `/v2/signals/by-ticker/{ticker}` | `routes/signals.py` | Tekil ticker sinyal gecmisi |
| GET | `/v2/signals/runs` | `routes/signals.py` | Calistirma metadata + zaman damgasi (sayfalı) |
| GET | `/v2/signals/run/{run_id}` | `routes/signals.py` | Belirli calistirma detayi |
| GET | `/v2/portfolio` | `routes/portfolio.py` | Guncel portfolio anlık goruntüsü |
| GET | `/v2/portfolio/{market}` | `routes/portfolio.py` | Piyasa bazli portfolio |
| GET | `/v2/history/outcomes` | `routes/history.py` | Kapanmis/acik islem sonuclari |
| GET | `/v2/history/calibration` | `routes/history.py` | Platt model kalibrasyon durumu |
| GET | `/v2/watchlist/{user_id}` | `routes/watchlist.py` | Kullanici izleme listesi |
| POST | `/v2/watchlist/{user_id}/add` | `routes/watchlist.py` | Izleme listesine ticker ekle |
| POST | `/v2/watchlist/{user_id}/remove` | `routes/watchlist.py` | Izleme listesinden cikar |
| POST | `/v2/trigger/run` | `routes/trigger.py` | Admin: pipeline'i manuel tetikle |
| POST | `/v2/trigger/update-outcomes` | `routes/trigger.py` | Admin: sonuclari guncelle + kalibre et |
| WS | `/v2/ws/live` | `routes/ws_live.py` | WebSocket canli sinyal akisi |
| GET | `/commodities` | `main.py` | Canli altin/gumus/USD-TRY (ucretsiz) |

## Legacy v1 Endpoints (`api/server.py`)

Geriye uyumluluk icin korunur:

| Method | Path | Amac |
|--------|------|------|
| GET | `/health` | Sistem durumu |
| GET | `/signals/latest` | Son sinyaller |
| POST | `/signals/generate` | Sinyal uret |
| GET | `/portfolio` | Portfolio |
| POST | `/portfolio/refresh` | Portfolio yenile |

## CORS Ayarlari

- `localhost:3000` (Dashboard)
- `localhost:5173` (Vue frontend)
- Vercel deploy URL'leri

## Auth

Bearer token dogrulamasi: `api/auth.py`. Admin endpoint'ler (trigger) icin zorunlu.
