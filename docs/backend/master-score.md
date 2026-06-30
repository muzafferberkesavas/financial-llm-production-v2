# Master Scorecard — 56 Kriter Puanlama Tablosu

Swing trading aday seciminde kullanilan deterministik puanlama sistemi.
Stage 1C'de hesaplanir, Stage 2 (LLM screen) yerine gecmistir.

- **Toplam**: 56 kriter, 10 kategori, max 225 puan
- **Esik**: master_score_pct >= %50 → Stage 3'e gecis hakki
- **Siralama**: Esigi gecenler puana gore sirali, top N Stage 3'e gider

## Label Esikleri

| Yuzde   | Label    |
|---------|----------|
| >= %80  | MUKEMMEL |
| >= %65  | IYI      |
| >= %50  | ORTA     |
| >= %35  | ZAYIF    |
| < %35   | KOTU     |

## A. TREND (9 kriter, max 40 puan)

| #   | Kriter                | Max | Kaynak             | Aciklama |
|-----|-----------------------|-----|--------------------|----------|
| c01 | weekly_trend_direction| 6   | weekly_trend       | UPTREND=6, EARLY_RECOVERY=4, SIDEWAYS=2, diger=0 |
| c02 | price_vs_sma200       | 5   | price_vs_sma200    | %10+ ustu=5, %3+=4, 0+=3, %-5+=1, diger=0 |
| c03 | sma50_vs_sma200       | 4   | sma50_vs_sma200    | Golden cross mesafesi |
| c04 | adx_trend_strength    | 5   | adx_14             | >=35=5, >=25=4, >=20=2, <20=0 |
| c05 | supertrend_direction  | 3   | supertrend_dir     | 1=3, -1=0 |
| c06 | ichimoku_cloud        | 5   | ichi_signal        | Bulut ustu=5, icinde=2, alti=0 |
| c07 | aroon_oscillator      | 4   | aroon_osc          | >60=4, >30=3, >0=2, <=-30=0 |
| c52 | close_vs_ema21        | 4   | close, ema21       | EMA21 uzerinde mesafe: %3+=4, %1+=3, 0+=2, %-2+=1 |
| c53 | close_vs_ema50        | 4   | close, ema50       | EMA50 uzerinde mesafe: %5+=4, %2+=3, 0+=2, %-3+=1 |

## B. MOMENTUM (8 kriter, max 33 puan)

| #   | Kriter            | Max | Kaynak               | Aciklama |
|-----|-------------------|-----|----------------------|----------|
| c08 | rsi_sweet_spot    | 5   | rsi_14, prev_rsi_14  | 50-65 sweet spot + yon bilgisi (yukseliyor mu?) |
| c09 | macd_histogram    | 5   | macd_hist, prev_macd_hist | Gercek capraz tespiti: prev<=0 & now>0 = 5 |
| c10 | stochastic        | 5   | stoch_k, stoch_d     | K>D oversold=5, K>D normal=4, K>80=1 |
| c11 | roc_10            | 4   | roc_10, prev_roc_10  | %3-10=4, ivmelenme bonusu |
| c12 | williams_r        | 4   | willr_14             | -50 ile -20 arasi=4 |
| c13 | weekly_rsi        | 4   | weekly_rsi           | 50-70=4, 40-50=3 |
| c14 | cci_20            | 3   | cci_20               | 50-200=3, 0-50=2 |
| c51 | green_day         | 3   | close, prev_close    | Yesil gun: %2+=3, %0.5+=2, 0+=1 |

## C. HACIM (6 kriter, max 28 puan)

| #   | Kriter              | Max | Kaynak                 | Aciklama |
|-----|---------------------|-----|------------------------|----------|
| c15 | volume_ratio        | 6   | vol_ratio              | >=2x=6, >=1.5x=5, >=1.2x=3 |
| c16 | obv_trend           | 5   | obv_trend, obv_ema10/30| EMA(10)>EMA(30) trend kontrolu + RISING=5 |
| c17 | obv_divergence      | 5   | obv_divergence_type    | POSITIVE=5, NEGATIVE=0, yok+RISING=4 |
| c18 | money_flow_index    | 4   | mfi_14                 | 40-70=4, 70-80=3, 30-40=2 |
| c19 | chaikin_money_flow  | 4   | cmf_20                 | >0.10=4, >0.05=3, >0=2 |
| c20 | daily_dollar_volume | 4   | close*vol_sma_20       | Capraz-kesit yuzdelik siralama |

## D. VOLATILITE (5 kriter, max 19 puan)

| #   | Kriter            | Max | Kaynak           | Aciklama |
|-----|-------------------|-----|------------------|----------|
| c21 | bb_position       | 4   | bb_pct           | %B 0.3-0.7=4, 0.05-0.3=3 |
| c22 | bb_squeeze        | 5   | bb_squeeze       | Squeeze=5, NARROWING=3 |
| c23 | volatility_ratio  | 4   | vol_20d, vol_60d | 20d < 60d*0.8=4 (daralma) |
| c24 | atr_percent       | 3   | atr_pct          | %2-5=3 (ideal swing araligi) |
| c54 | adr_fitness       | 3   | adr_pct          | %2.5-6=3 (swing icin ideal ADR) |

## E. FIYAT YAPISI (7 kriter, max 31 puan)

| #   | Kriter              | Max | Kaynak                  | Aciklama |
|-----|---------------------|-----|-------------------------|----------|
| c25 | fibonacci_zone      | 5   | fib_zone                | healthy_pullback=5, strong_zone=4 |
| c26 | price_vs_vwap       | 4   | price_vs_vwap           | VWAP hafif ustu=4 |
| c27 | donchian_position   | 5   | donch_pct               | 0.6-0.9=5 (yakindan yukselen) |
| c28 | 52w_high_proximity  | 5   | prices (high 252d)      | <%5 asagi=5, <%10=4 |
| c29 | swing_position      | 3   | swing_high/low_20       | Breakout=3, near high=2 |
| c55 | setup_pattern       | 5   | setup_type, confidence  | conf>=0.7=5, >=0.5=4, >=0.3=3 |
| c56 | candlestick_signal  | 4   | pattern_bull_engulf, pattern_hammer | Pattern + yuksek hacim=4, sadece pattern=2 |

## F. DEGER (5 kriter, max 18 puan)

| #   | Kriter                | Max | Kaynak              | Aciklama |
|-----|-----------------------|-----|---------------------|----------|
| c30 | pe_ratio_relative     | 4   | pe_ratio + pctile   | Capraz-kesit F/K quintile |
| c31 | pb_ratio_relative     | 3   | pb_ratio + pctile   | Capraz-kesit PD/DD quintile |
| c32 | ev_ebitda_relative    | 4   | ev_to_ebitda + pctile | Capraz-kesit EV/FAVOK quintile |
| c33 | forward_pe_vs_trailing| 4   | forward_pe/pe_ratio | <0.85=4 (kazanc artisi bekleniyor) |
| c34 | peg_ratio             | 3   | peg_ratio           | <1.0=3, <1.5=2 |

## G. KALITE (5 kriter, max 18 puan)

| #   | Kriter                | Max | Kaynak           | Aciklama |
|-----|-----------------------|-----|------------------|----------|
| c35 | roe_relative          | 4   | roe + pctile     | Capraz-kesit ROE quintile |
| c36 | profit_margin_relative| 4   | margin + pctile  | Capraz-kesit marj quintile |
| c37 | debt_equity_safety    | 4   | D/E + pctile     | Dusuk borc = yuksek puan |
| c38 | current_ratio         | 3   | current_ratio    | >2.0=3, >1.5=2 |
| c39 | free_cash_flow        | 3   | free_cash_flow   | Pozitif=3, negatif=0 |

## H. BUYUME (4 kriter, max 14 puan)

| #   | Kriter                | Max | Kaynak                  | Aciklama |
|-----|-----------------------|-----|-------------------------|----------|
| c40 | revenue_growth_relative| 4  | revenue_growth_yoy      | Capraz-kesit quintile |
| c41 | earnings_growth_relative| 4 | earnings_growth_yoy     | Capraz-kesit quintile |
| c42 | revenue_acceleration  | 3   | quarterly vs yoy growth | Ceyreklik > yillik = ivmeleniyor |
| c43 | earnings_surprise     | 3   | last_earnings_surprise  | >%5=3, >%2=2 |

## I. RISK YONETIMI (4 kriter, max 12 puan)

| #   | Kriter                    | Max | Kaynak                | Aciklama |
|-----|---------------------------|-----|-----------------------|----------|
| c44 | risk_reward_ratio         | 4   | swing_high/low, close | R:R >3=4, >2=3 |
| c45 | earnings_proximity        | 3   | days_to_earnings      | >30d=3, >15d=2, <=5d=0 |
| c46 | volatility_fitness        | 3   | vol_20d, atr_pct      | Ideal aralikta=3 |
| c47 | negative_divergence_penalty| 2  | obv_divergence_type   | NEGATIVE=0, diger=2 |

## J. COKLU ZAMAN DILIMI (3 kriter, max 12 puan)

| #   | Kriter              | Max | Kaynak                   | Aciklama |
|-----|---------------------|-----|--------------------------|----------|
| c48 | timeframe_alignment | 5   | timeframe_alignment      | ALIGNED=5, PARTIALLY=2, CONFLICTING=0 |
| c49 | ema_order           | 4   | ema12>ema26>sma50>sma200 | 3/3 sirali=4, 2/3=3, 1/3=2 |
| c50 | di_spread           | 3   | di_plus - di_minus       | >15=3, >5=2, >0=1 |

## Ozet

| Kategori       | Kriter Sayisi | Max Puan |
|----------------|:------------:|:--------:|
| TREND          | 9            | 40       |
| MOMENTUM       | 8            | 33       |
| HACIM          | 6            | 28       |
| VOLATILITE     | 5            | 19       |
| FIYAT_YAPISI   | 7            | 31       |
| DEGER          | 5            | 18       |
| KALITE         | 5            | 18       |
| BUYUME         | 4            | 14       |
| RISK           | 4            | 12       |
| COKLU_ZAMAN    | 3            | 12       |
| **TOPLAM**     | **56**       | **225**  |

## Pipeline Akisi (Stage 2 kaldirildi)

```
Stage 0   → Ingest (fiyat, fundamentals, haberler)
Stage 0B  → Market agenda (Haiku ile haber ceviri)
Stage 1   → Hard filter (veri, fiyat, piyasa degeri, hacim, dolar hacmi)
Stage 1B  → Setup detection (pullback_ema, bull_flag, breakout)
Stage 1C  → Indicators + Master Score (56 kriter) + Stage 3 Queue
             master_score >= %50 → top N → ctx.stage3_queue
Stage 3   → Deep LLM analiz (Opus)
Stage 4   → Multi-confirmation (master_score_pct >= %60 yeni kriter) + allocation
Stage 4.5 → Backtest gate
Stage 5   → Output
```
