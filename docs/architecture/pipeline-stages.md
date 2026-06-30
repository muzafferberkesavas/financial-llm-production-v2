# Pipeline Asamalari

Her asama `backend/src/finllm/pipeline/` altinda bagimsiz bir modul olarak yasar.
Orchestrator: `orchestrator.py` → `run_pipeline()`.

## Stage 0 — Data Ingest (`stage0_ingest.py`)

Fiyat verisi (yfinance OHLCV), teknik indikatörler ve makro kontekst cekilir.

## Stage 0b — News Agenda (`stage0b_agenda.py`)

Haber kaynakları taranır (Finnhub, KAP, SEC, RSS). Türkçe haberler Claude ile İngilizce'ye çevrilir. Piyasa gündemi oluşturulur.

## Stage 1 — Hard Filters (`stage1_filter.py`)

Volatilite, listeleme/çıkarma durumu gibi sert filtreler uygulanır. Uygunsuz hisseler elenir.

## Stage 1b — Setup Scoring (`stage1b_setup.py`)

10+ teknik indikatörün yakınsaması (confluence) üzerinden setup skoru hesaplanır.

## Stage 1c — Feature Matrix (`stage1c_features.py`)

Genişletilmiş özellik matrisi oluşturulur (teknik + temel + sentiment).

## Stage 2 — LLM Screening (`stage2_screen.py`)

**Model:** Haiku 4.5 (~$0.001/ticker)

Ucuz ve hızlı LLM taraması. Her ticker için `strong / potential / skip` kararı verilir. Top-N kota uygulanır.

## Stage 3 — Deep Analysis (`stage3_deep.py`)

**Model:** Opus (~$0.15/ticker)

Derinlemesine analiz. 7 seviyeli sinyal (GUCLU_AL → ACIL_SAT), fiyat senaryoları (base/bull/bear), çok katmanlı gerekçe.

## Stage 4 — Bull/Bear Debate (`stage4_judge.py`)

**Modeller:** Haiku (adversary) + Sonnet 4.6 (judge)

2 turlu panel tartışması. Adversary ayı vakasını çerçeveler, judge sentezler ve nihai karar verir. Maliyet: ~$0.020/hisse.

## Stage 4.5 — Backtest Gate (`stage4_5_backtest_gate.py`)

Walk-forward test ile sağlamlık doğrulaması. 5 hata tespiti. Next-bar fill, gerçekçi kayma. SMA200 ayı rejimi tespiti.

## Stage 5 — Signal Export (`stage5_writer.py`)

JSON export + sinyal loglama. Çıktılar `backend/data/out/` altına yazılır.

## Pipeline Context (`context.py`)

```python
class PipelineContext:
    adapter: MarketAdapter       # Piyasa adaptörü
    mode: str                    # pre_market / intraday / end_of_day
    run_id: str                  # Benzersiz çalışma kimliği
    total_capital: float         # Toplam sermaye
    signals: list[ExtendedSignal]
    actionable_signals: list[ExtendedSignal]
    stage_durations_sec: dict    # Aşama süreleri
    total_cost_usd: float        # Toplam LLM maliyeti
    regime: RegimeCheck | None   # Boğa/ayı/yatay rejim
    macro_context: MacroContext | None
```
