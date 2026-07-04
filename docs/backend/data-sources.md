# Veri Kaynaklari Raporu

Sistemin kullandigi tum veri kaynaklari, harici API'ler, cache mekanizmalari ve API key gereksinimleri.

---

## 1. Fiyat / OHLCV Verisi

| | |
|---|---|
| **Modul** | `backend/src/finllm/data/prices.py` |
| **Harici API** | `yfinance` (`yf.download()`) |
| **API Key** | Gerekmiyor (ucretsiz) |
| **Cache** | Parquet: `backend/data/cache/prices_{symbol}_{interval}.parquet` |
| **Cache Stratejisi** | Inkremental — sadece eksik tarih araligi indirilir (backfill + forward) |
| **Retry** | `tenacity` — 3 deneme, exponential backoff, 20s socket timeout |

**Parametreler:** `symbol`, `start` (default `2018-01-01`), `end` (bugun), `interval` (default `1d`)

**Donen kolonlar:** `open`, `high`, `low`, `close`, `volume` (kucuk harf), `date` index. `auto_adjust=True` (split/dividend ayarlanmis).

**Not:** BIST ticker'lari `.IS` son eki gerektirir (ornegin `THYAO.IS`).

---

## 2. Temel (Fundamental) Veriler

### 2a. Canli Fundamentals

| | |
|---|---|
| **Modul** | `backend/src/finllm/data/fundamentals.py` |
| **Harici API** | `yfinance.Ticker(symbol).info` (~80 alan, 1-3s/cagri) |
| **API Key** | Gerekmiyor |
| **Cache** | JSON: `backend/data/cache/fundamentals_{symbol}.json` |
| **Cache TTL** | 12 saat |
| **Retry** | `tenacity` — 2 deneme |

**`FundamentalSnapshot` alanlari:**

| Kategori | Alanlar |
|----------|---------|
| Piyasa | `market_cap`, `shares_outstanding`, `float_shares`, `short_ratio`, `avg_volume_10d`, `avg_volume` |
| Degerleme | `pe_ratio` (trailing), `forward_pe`, `pb_ratio`, `price_to_sales`, `ev_to_ebitda`, `ev_to_revenue`, `peg_ratio` |
| Karlilik | `profit_margin`, `gross_margin`, `operating_margin`, `roe`, `roa` |
| Buyume | `revenue_growth_yoy`, `earnings_growth_yoy`, `revenue_growth_quarterly`, `earnings_growth_quarterly` |
| Bilanco | `debt_to_equity`, `current_ratio`, `quick_ratio`, `total_cash`, `total_debt`, `free_cash_flow`, `book_value` |
| Temettü | `dividend_yield`, `payout_ratio`, `five_year_avg_dividend_yield` |
| Takvim | `days_to_earnings` (yf.Ticker.earnings_dates'den sonraki tarih) |
| Meta | `sector`, `industry`, `country` |

### 2b. Point-in-Time Fundamentals (Backtest icin)

| | |
|---|---|
| **Modul** | `backend/src/finllm/data/finnhub_pit.py` |
| **Harici API** | Finnhub `/stock/financials-reported` (yillik 10-K dosyalamalari) |
| **API Key** | **Gerekli:** `FINNHUB_API_KEY` |
| **Cache** | In-process dict (oturum suresi) |

`filedDate` kullanilarak look-ahead bias onlenir. US-GAAP kavramlari eslenir:

| Alan | Aciklama |
|------|----------|
| `revenue`, `net_income`, `eps_diluted` | Gelir tablosu |
| `equity`, `total_debt`, `current_assets`, `current_liabilities` | Bilanco |
| `op_cash_flow`, `capex` | Nakit akim |
| `roe`, `profit_margin`, `debt_to_equity`, `current_ratio` | Turetilmis oranlar |
| `free_cash_flow` | op_cash_flow - capex |
| `revenue_growth_yoy`, `earnings_growth_yoy` | Buyume |

**Not:** P/E ve P/B kasitli olarak dahil edilmez (gecmis fiyat/EPS uyumsuzlugu riski).

---

## 3. Ceyreklik Finansallar

| | |
|---|---|
| **Modul** | `backend/src/finllm/data/quarterly_financials.py` |
| **Harici API** | `yfinance.Ticker(symbol).quarterly_financials`, `.quarterly_balance_sheet`, `.quarterly_cashflow` |
| **API Key** | Gerekmiyor |
| **Cache** | JSON: `backend/data/cache/quarterly/{ticker}.json` |
| **Cache TTL** | 45 gun |

**Son 4 ceyrek icin donen alanlar:**

| Kategori | Alanlar |
|----------|---------|
| Gelir tablosu | `revenue`, `net_income`, `gross_margin`, `operating_margin`, `net_margin` |
| Bilanco | `total_debt`, `total_equity`, `total_assets` |
| Nakit akim | `free_cash_flow` (Operating CF - CapEx), `capex` |

Donem etiketi: `YYYY-QN` formati.

---

## 4. Teknik Gostergeler

| | |
|---|---|
| **Modul** | `backend/src/finllm/features/technical.py` |
| **Kutuphane** | `pandas-ta-classic` (deprecated `pandas-ta` yerine) |
| **Girdi** | OHLCV DataFrame (prices) |
| **Cikti** | ~50+ kolon ekli DataFrame |

**Hesaplanan gostergeler:**

| Kategori | Gostergeler |
|----------|-------------|
| Getiri & Volatilite | `ret_1d`, `ret_5d`, `ret_20d`, `log_ret`, `vol_20d` (yilliklandirilmis), `vol_60d` |
| Trend / MA | `sma_10/20/50/200`, `ema_12/26`, `price_vs_sma20/50/200`, `sma50_vs_sma200` |
| Momentum | `rsi_14`, `rsi_7`, `macd`, `macd_signal`, `macd_hist`, `stoch_k`, `stoch_d`, `cci_20`, `willr_14`, `roc_10` |
| Volatilite | `bb_lower/mid/upper`, `bb_pct`, `bb_width`, `atr_14`, `atr_pct`, `donch_lower/upper/pct` |
| Hacim | `vol_sma_20`, `vol_ratio`, `obv`, `mfi_14`, `cmf_20`, `vwap_20`, `price_vs_vwap` |
| Trend Gucu | `adx_14`, `di_plus`, `di_minus`, `aroon_down/up/osc` |
| Ichimoku | `ichi_tenkan`, `ichi_kijun`, `ichi_senkou_a`, `ichi_senkou_b`, `ichi_signal` (+1/0/-1) |
| SuperTrend | `supertrend`, `supertrend_dir` |
| Mum Formasyonu | `candle_body_pct`, `candle_upper_shadow`, `candle_lower_shadow`, `pattern_bull_engulf`, `pattern_bear_engulf`, `pattern_hammer`, `pattern_doji` |
| Goreli Guc | `rs_spy`, `rs_spy_20d`, `rs_spy_60d` (SPY benchmark'ina karsi) |

---

## 5. Turetilmis (Derived) Gostergeler

| | |
|---|---|
| **Modul** | `backend/src/finllm/indicators/derived.py` |
| **Girdi** | Teknik gostergeli DataFrame + ham fiyat |
| **Kullanim** | Stage 1C'de `Candidate.indicators` dict'ine yazilir |

| Gosterge | Fonksiyon | Cikti |
|----------|-----------|-------|
| OBV Divergence | `compute_obv_divergence()` | `trend` (RISING/FALLING), `divergence` (bool), `type` (POSITIVE/NEGATIVE), `obv_ma20`, `obv_ema10`, `obv_ema30` |
| BB Squeeze | `compute_bb_squeeze()` | `width`, `trend` (NARROWING/WIDENING/STABLE), `squeeze` (bool) |
| Haftalik Trend | `compute_weekly_trend()` | `sma20`, `sma50`, weekly `rsi`, `trend` (UPTREND/DOWNTREND/EARLY_RECOVERY/EARLY_WEAKNESS/SIDEWAYS) |
| Swing Seviyeleri | `compute_swing_levels()` | `swing_high`, `swing_low` (20 gunluk) |
| Piyasa Rejimi | `detect_market_regime()` | STRONG_TREND / TREND / RANGE_SQUEEZE / RANGE / VOLATILE / TRANSITIONAL |

**Ek turetilmis skorlar:**

| Skor | Modul | Aciklama |
|------|-------|----------|
| Momentum 12-1 | `indicators/momentum.py` | 12-1 ay fiyat momentum faktoru (son ay haric, kisa vadeli reversal icin) |
| PEAD | `indicators/pead.py` | Post-earnings drift skoru, 0-100, bilancodan 75 gun sonrasina decay |
| Confluence | `indicators/confluence.py` | 8 bilesenden 100 puanlik birlesmis sinyal (weekly 20 + ADX 15 + RSI 15 + MACD 12 + volume 12 + OBV 10 + BB 8 + Fib 8) |
| Fundamental Score | `indicators/fundamentals.py` | 100 puanlik temel skor (value 40 + quality 30 + growth 30) sektor benchmark'larina karsi |
| Risk/Reward | `indicators/risk_reward.py` | Fundamental score + PEAD + analyst consensus bilesimi → reward, risk, composite (0-100) |

**Slope ve S/R yardimcilari:**

| Modul | Fonksiyonlar |
|-------|-------------|
| `scorecard/_slope_helpers.py` | `indicator_slope()` (linreg), `slopes_rising_count()`, `consecutive_growth()` |
| `scorecard/_sr_helpers.py` | `compute_fibonacci_sr()`, `compute_volume_profile_simple()`, `detect_pivot_lows()`, `breakout_age()`, `find_nearest_support/resistance()`, `count_support_touches()`, `is_higher_low_sequence()` |
| `scorecard/_setup_helpers.py` | `detect_setup()` — pullback_ema, bull_flag, breakout pattern tespiti |

---

## 6. Haber ve Aciklama Verileri

### 6a. KAP Bildirimleri (BIST)

| | |
|---|---|
| **Modul** | `backend/src/finllm/data/news/kap_reader.py` |
| **Harici API** | `https://www.kap.org.tr/tr/api/disclosures` (dokumantasyonsuz, herkese acik GET) |
| **API Key** | Gerekmiyor |
| **Cache** | JSON: `backend/data/cache/kap/{TICKER}_YYYYMMDD.json` (30 gun TTL) |

**Alanlar:** `ticker` (stockCode), `publish_date`, `title`, `disclosure_type`, `summary`, `url`, `priority` (HIGH/MEDIUM/LOW)

**Ek:** `pykap` kutuphanesi ile `BISTCompany.get_disclosures()` ve `get_financial_reports()`. Tipler: KDP, DEG, UNV, FAR, SYI.

**Ceviri:** `kap_translator.py` — kural tabanli TR→EN tip esleme (~40 giris), LLM maliyeti yok.

### 6b. Finnhub Sirket Haberleri (NASDAQ)

| | |
|---|---|
| **Modul** | `backend/src/finllm/data/news/finnhub_reader.py` |
| **Harici API** | Finnhub `/company-news` |
| **API Key** | **Gerekli:** `FINNHUB_API_KEY` |
| **Rate Limit** | Ucretsiz tier: 60 istek/dakika |

**Alanlar:** `headline`, `summary`, `published_at`, `source`, `url`, `ticker`

### 6c. SEC EDGAR Dosyalamalari (NASDAQ)

| | |
|---|---|
| **Modul** | `backend/src/finllm/data/news/sec_reader.py` |
| **Harici API** | `https://www.sec.gov/cgi-bin/browse-edgar` (Atom feed) |
| **API Key** | Gerekmiyor (herkese acik) |
| **Rate Limit** | 10 istek/saniye |

**Dosyalama tipleri:** `8-K` (onemli olaylar, HIGH), `10-Q` (ceyreklik rapor, MEDIUM)

**Alanlar:** `title`, `date`, `url`, `filing_type`

### 6d. RSS Haber Akislari

| | |
|---|---|
| **Modul** | `backend/src/finllm/data/news/rss_reader.py` |
| **API Key** | Gerekmiyor |

| Pazar | Kaynak | URL |
|-------|--------|-----|
| BIST | BigPara | `bigpara.hurriyet.com.tr/rss/` |
| BIST | Bloomberg HT | `bloomberght.com/rss` |
| BIST | Investing.com TR | `tr.investing.com/rss/news.rss` |
| BIST | ParaAnaliz | `paraanaliz.com/feed/` |
| BIST | NTV Ekonomi | `ntv.com.tr/ekonomi.rss` |
| NASDAQ | MarketWatch | `feeds.content.dowjones.io/...` |
| NASDAQ | Seeking Alpha | `seekingalpha.com/market_currents.xml` |
| NASDAQ | CNBC | `search.cnbc.com/rs/...` |

**Alanlar:** `title`, `description`, `pub_date`, `source`, `language`, `category` (STOCK/MACRO/REGULATORY), `url`

### 6e. BIST Hisse Haberleri

| | |
|---|---|
| **Modul** | `backend/src/finllm/data/news/bist_stock_news.py` |

RSS haberlerini BIST-100 sirket adlarina gore eslestirir. Turk finansal haberler sirket adi kullanir ("Akbank"), ticker degil ("AKBNK").

---

## 7. Piyasa Gundemi (Market Agenda)

| | |
|---|---|
| **Modul** | `backend/src/finllm/pipeline/stage0b_agenda.py` |
| **LLM** | Claude Haiku (`claude-haiku-4-5-20251001`) |
| **Maliyet** | ~$0.005/calisma |
| **Cache** | In-memory, 60 dakika TTL |

**Surec:**
1. Piyasa geneli RSS haberleri cekilir
2. NASDAQ: Ticker bazli Finnhub + SEC EDGAR haberleri (ThreadPoolExecutor, max 6 worker)
3. BIST: Watchlist icin toplu KAP bildirimleri
4. Claude Haiku tum ogelerden yapilandirilmis Ingilizce `MARKET AGENDA` olusturur (max 10 gundem maddesi, her biri <=350 karakter, `produce_agenda` tool call)

---

## 8. Makroekonomik Veriler

### 8a. FRED (ABD Makro)

| | |
|---|---|
| **Modul** | `backend/src/finllm/data/fred.py` |
| **Harici API** | `https://api.stlouisfed.org/fred/series/observations` |
| **API Key** | **Onerilen:** `FRED_API_KEY` (ucretsiz kayit) |

| Seri Kodu | Aciklama |
|-----------|----------|
| `CPIAUCSL` | TUFE (tum sehir, mevsim ayarli) → YoY % |
| `PCEPILFE` | Cekirdek PCE fiyat endeksi → YoY % |
| `UNRATE` | Issizlik orani |
| `PAYEMS` | Tarim disi istihdam → AoA degisim (NFP) |
| `FEDFUNDS` | Efektif federal fonlar faiz orani |
| `DGS10` | 10 yillik Hazine getirisi |
| `DGS2` | 2 yillik Hazine getirisi |

**Cikti:** `[RATES]` (2s10s spread), `[INFLATION]` (YoY enflasyon), `[EMPLOYMENT]` (NFP) blok formati.

**Fallback:** FRED key yoksa yfinance hazine ticker'lari (`^TNX`, `^IRX`) kullanilir.

### 8b. TCMB EVDS (Turk Makro)

| | |
|---|---|
| **Modul** | `backend/src/finllm/data/tcmb.py` |
| **Harici API** | `https://evds3.tcmb.gov.tr/igmevdsms-dis` (EVDS REST) |
| **API Key** | **Gerekli:** `TCMB_API_KEY` (ucretsiz, evds2.tcmb.gov.tr'den kayit) |

| Seri Kodu | Aciklama |
|-----------|----------|
| `TP.APIFON4` | 1 haftalik repo (politika) faizi % |
| `TP.FG.J0` | TUFE endeksi (aylik) → YoY % |
| `TP.DK.USD.A.YTL` | USD alis kuru (gunluk) → 3 aylik degisim |

**Cikti:** `[TURK MAKRO — TCMB]` blok formati.

### 8c. Makro Birlestiricisi

| | |
|---|---|
| **Modul** | `backend/src/finllm/data/macro.py` |
| **API Key** | Gerekmiyor (yfinance ucretsiz ticker'lar) |

**Izlenen yfinance ticker'lar:**

| Ticker | Aciklama |
|--------|----------|
| `^VIX` | Volatilite endeksi |
| `SPY` | S&P 500 ETF |
| `QQQ` | Nasdaq 100 ETF |
| `^TNX` | ABD 10 yillik getiri |
| `^IRX` | ABD 13 haftalik T-bill |
| `DX-Y.NYB` | USD DXY endeksi |
| `GC=F` | Altin (USD/ons) |
| `CL=F` | WTI ham petrol |
| `XU100.IS` | BIST-100 endeksi |
| `USDTRY=X` | USD/TRY kuru |

Her ticker icin 5g ve 20g % degisim + 200 gunluk HO pozisyonu hesaplanir.

---

## 9. Analist Verileri

| | |
|---|---|
| **Modul** | `backend/src/finllm/data/finnhub_fundamentals.py` |
| **Harici API** | Finnhub `/stock/earnings` + `/stock/recommendation` |
| **API Key** | **Gerekli:** `FINNHUB_API_KEY` |
| **Rate Limit** | Ucretsiz tier: 60 istek/dakika |
| **Cache** | JSON: `backend/data/cache/finnhub/{symbol}_YYYYMMDD.json` (gunluk) |

**`FinnhubSignals` alanlari:**

| Alan | Aciklama |
|------|----------|
| `avg_surprise_pct` | Son 4 ceyrek ortalama surpriz % |
| `beat_streak` | Ardisik beklenti asan ceyrek sayisi |
| `n_quarters` | Veri olan ceyrek sayisi |
| `earnings_momentum` | `beating` / `mixed` / `missing` / `unknown` |
| `analyst_score` | 0-1 arasi (strongBuy=1.0, buy=0.75, hold=0.5, sell=0.25, strongSell=0.0) |
| `analyst_label` | `bullish` (>=0.70) / `neutral` / `bearish` (<=0.45) |
| `n_analysts` | En son donemdeki analist sayisi |
| `last_earnings_date` | Son raporlanan donem (PEAD icin) |
| `last_surprise_pct` | O ceyrege ait EPS surpriz % |

---

## 10. Emtia Verileri

| | |
|---|---|
| **Modul** | `backend/src/finllm/data/commodities.py` |
| **Harici API** | yfinance (ucretsiz) |
| **Cache** | `fetch_prices()` parquet cache'i kullanir (60 gunluk pencere) |

| Ticker | Aciklama |
|--------|----------|
| `GC=F` | Altin (USD/ons) |
| `SI=F` | Gumus (USD/ons) |
| `USDTRY=X` | USD/TRY |

**Turetilmis:** `gold_try_gram` = (altin_usd / 31.1035) x USDTRY

---

## 11. Evren Tanimlari

| | |
|---|---|
| **Modul (NASDAQ)** | `backend/src/finllm/config/universe.py` |
| **Modul (BIST)** | `backend/src/finllm/markets/universes/bist_100.py` |

| Evren | Icerik |
|-------|--------|
| `US_CORE` | 47 ABD buyuk sermayeli hisse + ETF |
| `US_HIGH_BETA` | 13 spekulatif hisse |
| `DEFAULT_UNIVERSE` | US_CORE + US_HIGH_BETA birlesmis |
| `US_TEST` | [NVDA, MSFT] (test icin) |
| `BIST_100_TICKERS` | Tam BIST-100 listesi — `Ticker(symbol, market, name, sector)` tuple'lari, sektor adlari Turkce |

---

## 12. LLM Servisleri

| | |
|---|---|
| **Modul** | `backend/src/finllm/llm/claude.py` |
| **API Key** | **Gerekli:** `ANTHROPIC_API_KEY` |

| Model | Kullanim | Yaklasik Maliyet |
|-------|----------|------------------|
| Claude Haiku 4.5 | Market agenda ozetleme (Stage 0B) | ~$0.005/calisma |
| Claude Sonnet 4.6 | Hizli tarama/screen (Stage 2 — kaldirildi, backtest LLM eval icin) | ~$0.01-0.03/hisse |
| Claude Opus 4.6 | Derin analiz (Stage 3) | ~$0.05-0.15/hisse |

---

## API Key Ozet Tablosu

| Kaynak | Key Degiskeni | Zorunluluk | Maliyet |
|--------|---------------|------------|---------|
| yfinance (fiyat, fundamental, ceyreklik) | — | Yok | Ucretsiz |
| RSS akislari (BigPara, Bloomberg HT, CNBC, MarketWatch vb.) | — | Yok | Ucretsiz |
| SEC EDGAR (8-K, 10-Q) | — | Yok | Ucretsiz |
| KAP bildirimleri | — | Yok | Ucretsiz |
| FRED (ABD makro) | `FRED_API_KEY` | Onerilen | Ucretsiz (kayit gerekir) |
| Finnhub (haber, bilancorapor, analist, PIT) | `FINNHUB_API_KEY` | **Gerekli** | Ucretsiz tier (60 req/dk) |
| TCMB EVDS (Turk makro) | `TCMB_API_KEY` | **Gerekli** (BIST icin) | Ucretsiz (kayit gerekir) |
| Anthropic Claude | `ANTHROPIC_API_KEY` | **Gerekli** | Kullanima bagli |

---

## Cache Dizin Yapisi

```
backend/data/cache/
  prices_{symbol}_{interval}.parquet   # Fiyat verisi (inkremental)
  fundamentals_{symbol}.json           # Temel veriler (12 saat TTL)
  quarterly/{ticker}.json              # Ceyreklik finansallar (45 gun TTL)
  finnhub/{symbol}_YYYYMMDD.json       # Analist + bilancorapor (gunluk)
  kap/{TICKER}_YYYYMMDD.json           # KAP bildirimleri (30 gun TTL)
```

## Veri Akis Diyagrami

```
                    yfinance (ucretsiz)
                   /        |         \
              Fiyat    Fundamental   Ceyreklik
             (OHLCV)   (Snapshot)   (Finansal)
                |           |           |
                v           v           v
        +---> add_technical_features()
        |           |
        |     50+ teknik gosterge
        |           |
        |     +---> compute_* (derived)
        |     |     OBV div, BB squeeze,
        |     |     weekly trend, swing, regime
        |     |
        |     +---> compute_master_score()
        |           70 kriter, 277 max puan
        |
   Finnhub -----> Analist verileri + PIT fundamentals
        |              |
   KAP/RSS/SEC -> Haberler + Bildirimler
        |              |
   FRED/TCMB ----> Makro veriler
        |              |
        +-------> Stage 0B: Claude Haiku → Market Agenda
                       |
                 Stage 1C: Indicators + Master Score
                       |
                 Stage 3: Claude Opus → Derin Analiz
                       |
                 Stage 4-5: Sinyal + Cikti
```
