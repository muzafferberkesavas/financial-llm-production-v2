# CLI Scriptleri

Tum scriptler `backend/scripts/` altında bulunur.

## Ana Scriptler

| Script | Amac | Ornek Kullanim |
|--------|------|----------------|
| `run_funnel.py` | Tam pipeline calistirma | `--market {bist,nasdaq} --llm {mock,claude} --mode {pre_market,intraday,end_of_day} --capital 10000 --quota 12` |
| `run_decision_panel.py` | Top-N tartisma + export | `--market bist --symbols THYAO.IS,GARAN.IS --no-debate --no-macro --top-n 5 --export` |
| `daily_refresh.py` | Portfolio yenileme | `--mode {pre_open,post_close,manual} --universe bist` |
| `run_api.py` | API sunucusu baslat | (uvicorn wrapper) |

## Sinyal Uretimi

| Script | Amac |
|--------|------|
| `generate_signal.py` | Tekil sembol sinyal uretimi |
| `update_outcomes.py` | Islem sonuclarini guncelle |
| `migrate_json_to_db.py` | Eski JSON sinyallerini DB'ye tasi |

## Backtesting

| Script | Amac | Ornek Kullanim |
|--------|------|----------------|
| `backtest.py` | Tam backtest | `--universe {bist,sp500} --start 2022-01-01 --end 2024-12-31 --costs {midas-us,midas-bist,zero}` |
| `walkforward.py` | Walk-forward test | `--symbols AAPL,MSFT --window-size 60 --costs midas-us` |
| `calibrate_from_backtest.py` | Platt scaling | `--universe bist --outcomes-file outcomes.json` |

## Veri Indirme

| Script | Amac |
|--------|------|
| `fetch_sp500_universe.py` | S&P 500 sembol listesi indir |
| `fetch_bist100_universe.py` | BIST 100 sembol listesi indir |

## Diger

| Script | Amac |
|--------|------|
| `smoke_test.py` | Entegrasyon saglik kontrolu (argumansiz) |
| `telegram_dm_bot.py` | Telegram DM sinyal iletimi (sidecar) |
| `measure_macro_lift.py` | Makro overlay katma degerini olc |
| `meta_label_llm_test.py` | LLM meta-etiket etkisi analizi |
