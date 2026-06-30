# Test Altyapisi

## Araclar

- **pytest** + **pytest-asyncio** — Unit/integration testler
- **ruff** — Linting
- **mypy** — Tip kontrolu

## Pytest Yapilandirmasi

`pyproject.toml` icinde:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

## Test Calistirma

```bash
cd backend

# Unit testler
.venv/bin/pytest tests/

# Smoke test (entegrasyon)
.venv/bin/python scripts/smoke_test.py

# Backtest (kalite kapisi olarak)
.venv/bin/python scripts/backtest.py --universe bist --start 2022-01-01 --end 2024-12-31
```

## Test Tipleri

### Unit Testler (`backend/tests/`)
Dizin mevcut ancak icerik minimal. Genisletilmeye acik.

### Entegrasyon Testleri (Script bazli)
| Script | Test Ettigi |
|--------|-------------|
| `smoke_test.py` | Fiyat cekme, teknik indikatörler, sentiment |
| `test_macro_sector.py` | Makro kontekst + sektor istahi |
| `test_portfolio.py` | Pozisyon boyutlandirma, cikislar |
| `test_sector_gate.py` | Sektor filtreleme |
| `test_risk_reward.py` | Risk/getiri skorlama |
| `test_ranking.py` | Sinyal siralama |

### Backtest (QA olarak)
Walk-forward backtest birincil kalite kapisi gorevi gorur:
- `scripts/backtest.py` — Universe backtest
- `scripts/walkforward.py` — Cok pencereli cross-validation
- 5 hata tespiti, next-bar fill, gercekci kayma

## Mock LLM

`--llm mock` ile tüm testler API key olmadan calistirilabilir. `llm/mock.py` deterministik sonuclar uretir.

## Mevcut Durum

Test coverage minimal. Backtest walk-forward birincil kalite mekanizmasi olarak kullanilmakta. Unit test genisletmesi oncelikli bir gap.
