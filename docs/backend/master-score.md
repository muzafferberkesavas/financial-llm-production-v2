# Master Scorecard — 70 Kriter Puanlama Tablosu

Swing trading aday seciminde kullanilan deterministik puanlama sistemi.
Stage 1C'de hesaplanir, Stage 2 (LLM screen) yerine gecmistir.

- **Toplam**: 70 kriter, 10 kategori, max 277 puan
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
| c03 | sma50_vs_sma200       | 4   | sma50_vs_sma200    | Golden cross mesafesi: %5+=4, 0+=3, %-2+=2, diger=0 |
| c04 | adx_trend_strength    | 5   | adx_14             | >=35=5, >=25=4, >=20=2, <20=0 |
| c05 | supertrend_direction  | 3   | supertrend_dir     | 1=3, -1=0 |
| c06 | ichimoku_cloud        | 5   | ichi_signal        | Bulut ustu(1)=5, icinde(0)=2, alti(-1)=0 |
| c07 | aroon_oscillator      | 4   | aroon_osc          | >60=4, >30=3, >0=2, <=0=0 |
| c52 | close_vs_ema21        | 4   | close, ema21       | EMA21 uzerinde mesafe: %3+=4, %1+=3, 0+=2, %-2+=1, diger=0 |
| c53 | close_vs_ema50        | 4   | close, ema50       | EMA50 uzerinde mesafe: %5+=4, %2+=3, 0+=2, %-3+=1, diger=0 |

## B. MOMENTUM (9 kriter, max 38 puan)

| #   | Kriter              | Max | Kaynak                    | Aciklama |
|-----|---------------------|-----|---------------------------|----------|
| c08 | rsi_sweet_spot      | 5   | rsi_14, prev_rsi_14       | 50-65 sweet spot + yukseliyor mu: rising=5, degil=4. 40-50: rising=4/3. 30-40: rising=4/2. <30: rising=3/1. >70=0 |
| c09 | macd_histogram      | 5   | macd_hist, prev_macd_hist | Gercek capraz: prev<=0 & now>0=5, pozitif+buyuyor=4, pozitif=3, negatif+azaliyor=2, negatif=0 |
| c10 | stochastic          | 5   | stoch_k, stoch_d          | K>D oversold(<20)=5, K>D normal(20-80)=4, K>80=1, K<20 & K<D=0 |
| c11 | roc_10              | 4   | roc_10, prev_roc_10       | %3-10=4, %1-3 ivmelenen=4/3, %10-15=2, >15=1, <0 ivmelenen=1 |
| c12 | williams_r          | 4   | willr_14                  | -50 ile -20=4, -80 ile -50=3, <-80=2, >-20=1 |
| c13 | weekly_rsi          | 4   | weekly_rsi                | 50-70=4, 40-50=3, >70=1, diger=0 |
| c51 | green_day           | 3   | close, prev_close         | Yesil gun: %2+=3, %0.5+=2, 0+=1, kirmizi=0 |
| c66 | indicator_momentum  | 4   | rsi/adx/macd 5-bar slope  | 3/3 rising=4, 2/3=3, 1/3=1, 0=0 |
| c67 | rsi_trajectory      | 4   | rsi_14, rsi_slope_10      | RSI 40-65 + rising=4, 30-40 rising=3, 50-70 falling=2, rising=1, diger=0 |

## C. HACIM (9 kriter, max 37 puan)

| #   | Kriter                 | Max | Kaynak                  | Aciklama |
|-----|------------------------|-----|-------------------------|----------|
| c15 | volume_ratio           | 6   | vol_ratio               | >=2x=6, >=1.5x=5, >=1.2x=3, >=0.8x=1, diger=0 |
| c16 | obv_trend              | 5   | obv_trend, obv_ema10/30 | RISING+EMA10>30=5, RISING+OBV>MA20=4, RISING=3, diger+EMA10>30=1, diger=0 |
| c17 | obv_divergence         | 5   | obv_divergence_type     | POSITIVE=5, NEGATIVE=0, yok+RISING=4, yok=2 |
| c18 | money_flow_index       | 4   | mfi_14                  | 40-70=4, 70-80=3, 30-40=2, >80=0, diger=1 |
| c19 | chaikin_money_flow     | 4   | cmf_20                  | >0.10=4, >0.05=3, >0=2, <=0=0 |
| c20 | daily_dollar_volume    | 4   | close*vol_sma_20        | Capraz-kesit yuzdelik siralama (quintile) |
| c68 | macd_hist_sequence     | 3   | macd_hist_values        | Histogram ardisik buyume: >=4=3, >=3=2, >=2=1, diger=0 |
| c69 | obv_slope_change       | 3   | obv_slope_5, obv_slope_20 | Kisa>0 & kisa>uzun=3, kisa>0=2, kisa<0 & uzun>0=1, diger=0 |
| c71 | volume_price_divergence| 3   | price_vol_corr_20       | Fiyat-hacim korelasyonu: >0.5=3, >0.2=2, >-0.2=1, diger=0 |

## D. VOLATILITE (4 kriter, max 16 puan)

| #    | Kriter              | Max | Kaynak              | Aciklama |
|------|---------------------|-----|---------------------|----------|
| c21  | bb_position         | 4   | bb_pct              | %B 0.3-0.7=4, 0.05-0.3=3, 0.7-0.9=2, <0.05=2, >0.9=0 |
| c22  | bb_squeeze          | 5   | bb_squeeze, bb_width_trend | Squeeze=5, NARROWING=3, WIDENING=2, STABLE=1 |
| c23  | volatility_ratio    | 4   | vol_20d, vol_60d    | 20d<60d*0.8=4 (daralma), 20d<60d=3, 20d>60d*1.3=1, diger=2 |
| c24m | swing_range_fitness | 3   | atr_pct, adr_pct    | ATR(%2-5)+ADR(%2.5-6) birlesmis ortalama, ideal=3 |

## E. FIYAT YAPISI (9 kriter, max 39 puan)

| #   | Kriter              | Max | Kaynak                  | Aciklama |
|-----|---------------------|-----|-------------------------|----------|
| c25 | fibonacci_zone      | 5   | fib_zone                | healthy_pullback=5, strong_zone/critical_support=4, breakout=3, deep_pullback=2, danger/broken=0 |
| c26 | price_vs_vwap       | 4   | price_vs_vwap           | VWAP hafif ustu(0-5%)=4, >=5%=3, -2% ile 0=2, diger=0 |
| c27 | donchian_position   | 5   | donch_pct               | 0.6-0.9=5, 0.4-0.6=3, >0.95=2, <0.3=0 |
| c28 | 52w_high_proximity  | 5   | prices (high 252d)      | <%5 asagi=5, <%10=4, <%20=3, <%30=1, diger=0 |
| c29 | swing_position      | 3   | swing_high/low_20       | Breakout(close>sh)=3, near high(>sh*0.98)=2, ust yari=1, diger=0 |
| c55 | setup_pattern       | 5   | setup_type, confidence  | conf>=0.7=5, >=0.5=4, >=0.3=3, diger=1, none=0 |
| c56 | candlestick_signal  | 3   | pattern_bull_engulf, pattern_hammer, vol_ratio | Pattern + hacim>=1.2x=3, hacimsiz=0 |
| c72 | support_proximity   | 5   | close, fib_supports     | Fibonacci destege mesafe: <%2=5, <%5=4, <%10=3, <%15=1, diger=0 |
| c73 | resistance_distance | 4   | close, fib_resistances  | Fibonacci dirence mesafe: >%15=4, >%10=3, >%5=2, >%2=1, diger=0 |

## F. DEGER (6 kriter, max 21 puan)

| #   | Kriter                | Max | Kaynak              | Aciklama |
|-----|-----------------------|-----|---------------------|----------|
| c30 | pe_ratio_relative     | 4   | pe_ratio + pctile   | Capraz-kesit F/K quintile. Abs: <8=4, <15=3, <25=2, diger=0 |
| c31 | pb_ratio_relative     | 3   | pb_ratio + pctile   | Capraz-kesit PD/DD quintile. Abs: <1.5=3, <3=2, diger=0 |
| c32 | ev_ebitda_relative    | 4   | ev_to_ebitda + pctile | Capraz-kesit EV/FAVOK quintile. Abs: <6=4, <10=3, <15=2, diger=0 |
| c33 | forward_pe_vs_trailing| 4   | forward_pe/pe_ratio | <0.85=4 (kazanc artisi bekleniyor), <1.0=3, =1.0=1, >1.0=0 |
| c34 | peg_ratio             | 3   | peg_ratio           | <=0=0 (neg EPS), <1.0=3, <1.5=2, <2.0=1, diger=0 |
| c58 | ev_sales_relative     | 3   | ev_to_revenue + pctile | Capraz-kesit EV/S quintile. Abs: <1=3, <3=2, <5=1, diger=0 |

## G. KALITE (7 kriter, max 25 puan)

| #    | Kriter                | Max | Kaynak              | Aciklama |
|------|-----------------------|-----|---------------------|----------|
| c35  | roe_relative          | 4   | roe + pctile        | Capraz-kesit ROE quintile. Abs: >%25=4, >%15=3, >%5=2, >0=1, <=0=0 |
| c36  | profit_margin_relative| 4   | margin + pctile     | Capraz-kesit marj quintile. Abs: >%20=4, >%10=3, >%5=2, >0=1, <=0=0 |
| c37  | debt_equity_safety    | 4   | D/E + pctile        | Dusuk borc = yuksek puan. Abs: <0.3=4, <0.7=3, <1.5=2, <2.5=1, diger=0 |
| c38  | current_ratio         | 3   | current_ratio       | >2.0=3, >1.5=2, >1.0=1, <=1.0=0 |
| c57  | fcf_yield             | 4   | free_cash_flow / market_cap | FCF yield: >%8=4, >%5=3, >%2=2, >0=1, <=0=0 |
| c62  | accruals_quality      | 3   | (net_income-OCF)/total_assets | Dusuk accrual=kaliteli gelir: <-0.05=3, <0.05=2, <0.10=1, diger=0 |
| c63p | analyst_consensus     | 3   | analyst_score (1-5) | >=4.0=3, >=3.5=2, >=3.0=1, diger=0 |

## H. BUYUME (6 kriter, max 20 puan)

| #   | Kriter                  | Max | Kaynak                  | Aciklama |
|-----|-------------------------|-----|-------------------------|----------|
| c40 | revenue_growth_relative | 4   | revenue_growth_yoy      | Capraz-kesit quintile. Abs: >%30=4, >%15=3, >%5=2, >0=1, <=0=0 |
| c41 | earnings_growth_relative| 4   | earnings_growth_yoy     | Capraz-kesit quintile. Abs: >%30=4, >%15=3, >%5=2, >0=1, <=0=0 |
| c42 | revenue_acceleration    | 3   | quarterly vs yoy growth | Ceyreklik > yillik=3, yaklasik esit=2, diger=0 |
| c43 | earnings_surprise       | 3   | last_earnings_surprise  | >%5=3, >%2=2, >0=1, <=0=0 |
| c61 | gross_margin_stability  | 3   | gross_margin_std (ceyreklik) | std<0.02=3, <0.05=2, <0.10=1, diger=0 |
| c64 | operating_leverage      | 3   | earnings_growth / revenue_growth | >2.0 & pozitif=3, >1.0 & pozitif=2, >0 & pozitif=1, diger=0 |

## I. RISK YONETIMI (3 kriter, max 11 puan)

| #   | Kriter              | Max | Kaynak                       | Aciklama |
|-----|---------------------|-----|------------------------------|----------|
| c45 | earnings_proximity  | 3   | days_to_earnings             | >30d=3, >15d=2, >5d=1, <=5d=0. N/A=2 (neutral) |
| c46 | volatility_fitness  | 3   | vol_20d, atr_pct             | vol 0.15-0.40 & ATR %1.5-5=3, vol 0.10-0.50 & ATR %1-7=2, diger=0 |
| c76 | rr_sr_based         | 5   | fib_supports, fib_resistances | Fib S/R bazli R:R: >4=5, >3=4, >2=3, >1.5=2, >1=1, diger=0 |

## J. COKLU ZAMAN DILIMI (8 kriter, max 30 puan)

| #   | Kriter                | Max | Kaynak                   | Aciklama |
|-----|-----------------------|-----|--------------------------|----------|
| c48 | timeframe_alignment   | 5   | timeframe_alignment      | ALIGNED=5, PARTIALLY=2, CONFLICTING=0, UNKNOWN=1 |
| c49 | ema_order             | 4   | ema12>ema26>sma50>sma200 | 3/3 sirali=4, 2/3=3, 1/3=2, 0=0 |
| c50 | di_spread             | 3   | di_plus - di_minus       | >15=3, >5=2, >0=1, <=0=0 |
| c74 | sr_touch_count        | 3   | fib_supports, prices     | En yakin destek 60d test sayisi: >=3=3, >=2=2, >=1=1, 0=0 |
| c75 | volume_profile_pos    | 4   | close, vpoc, va_high/low | VA ustu=4, POC ustu=3, VA icinde=2, VA alti=0 |
| c77 | consolidation_duration| 4   | prices (20d/60d range)   | 20d/60d<0.3=4, <0.5=3, <0.7=2, diger=0 |
| c78 | higher_low_sequence   | 4   | pivot_lows               | Ardisik higher low (Dow): >=3=4, >=2=3, >=1=2, 0=0 |
| c79 | breakout_age          | 3   | breakout_age_days, vol   | <=3d+hacim=3, <=3d=2, <=7d=1, diger=0 |

## Ozet

| Kategori       | Kriter Sayisi | Max Puan |
|----------------|:------------:|:--------:|
| TREND          | 9            | 40       |
| MOMENTUM       | 9            | 38       |
| HACIM          | 9            | 37       |
| VOLATILITE     | 4            | 16       |
| FIYAT_YAPISI   | 9            | 39       |
| DEGER          | 6            | 21       |
| KALITE         | 7            | 25       |
| BUYUME         | 6            | 20       |
| RISK           | 3            | 11       |
| COKLU_ZAMAN    | 8            | 30       |
| **TOPLAM**     | **70**       | **277**  |

## 56 -> 70 Kriter Degisiklik Ozeti

**Eklenen kriterler (14):**
- c58 ev_sales_relative (DEGER +3)
- c57 fcf_yield (KALITE +4, eski c39 binary FCF yerine)
- c62 accruals_quality (KALITE +3)
- c63p analyst_consensus (KALITE +3)
- c61 gross_margin_stability (BUYUME +3)
- c64 operating_leverage (BUYUME +3)
- c66 indicator_momentum (MOMENTUM +4)
- c67 rsi_trajectory (MOMENTUM +4)
- c68 macd_hist_sequence (HACIM +3)
- c69 obv_slope_change (HACIM +3)
- c71 volume_price_divergence (HACIM +3)
- c72 support_proximity (FIYAT_YAPISI +5)
- c73 resistance_distance (FIYAT_YAPISI +4)
- c74 sr_touch_count (COKLU_ZAMAN +3)
- c75 volume_profile_pos (COKLU_ZAMAN +4)
- c76 rr_sr_based (RISK +5, eski c44 basic R:R yerine)
- c77 consolidation_duration (COKLU_ZAMAN +4)
- c78 higher_low_sequence (COKLU_ZAMAN +4)
- c79 breakout_age (COKLU_ZAMAN +3)

**Kaldirilan/birlesen kriterler:**
- c14 cci_20 (MOMENTUM) — RSI/Stoch/WillR ile korelasyon, cikarildi
- c24 atr_percent + c54 adr_fitness → c24m swing_range_fitness (birlesti)
- c39 free_cash_flow (binary) → c57 fcf_yield (gelismis versiyon)
- c44 risk_reward_ratio → c76 rr_sr_based (Fibonacci bazli)
- c47 negative_divergence_penalty — c17 obv_divergence ile ayni veri, cikarildi
- c56 candlestick_signal max 4→3, hacim teyidi zorunlu

## Pipeline Akisi (Stage 2 kaldirildi)

```
Stage 0   → Ingest (fiyat, fundamentals, haberler)
Stage 0B  → Market agenda (Haiku ile haber ceviri)
Stage 1   → Hard filter (veri, fiyat, piyasa degeri, hacim, dolar hacmi)
Stage 1B  → Setup detection (pullback_ema, bull_flag, breakout) [Stage 1C'ye absorbe edildi]
Stage 1C  → Indicators + Master Score (70 kriter, 277 max) + Stage 3 Queue
             master_score >= %50 → top N → ctx.stage3_queue
Stage 3   → Deep LLM analiz (Opus)
Stage 4   → Multi-confirmation (master_score_pct >= %60 yeni kriter) + allocation
Stage 4.5 → Backtest gate
Stage 5   → Output
```
