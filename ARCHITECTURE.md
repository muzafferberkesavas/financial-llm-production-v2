# FinLLM — Sistem Mimarisi

> **Amaç:** LLM (Anthropic Claude) + quant hibrit, *genelden özele* (global makro → sektör → şirket) çalışan
> çok-piyasalı (US / BIST / Altın) alım-satım sinyal sistemi.
>
> Bu doküman, 2026-06 derin araştırmasının (21 birincil kaynak, çekişmeli doğrulama) bulgularını
> mevcut kod tabanına bağlar ve faz faz yol haritası verir. **Atıflar `[A1]…` biçiminde dipnotlardadır.**

---

## 0. Tasarım İlkeleri (kanıt-temelli)

1. **LLM-only değil, hibrit.** İki bağımsız akademik mimari aynı sonuca varıyor: "tek model tipi yetmez" — quant + LLM birlikte. `[A1][A2]`
2. **Katmanlı funnel.** 4 katman: Data Perception → Reasoning Engine → Strategy Generation → Execution & Control. `[A1][A2]`
3. **Rol-ayrıştırmalı multi-agent.** Uzman analist ajanları (fundamental/technical/sentiment/news) → bull-vs-bear debate → trader sentezi → risk katmanı. SOTA'da baskın desen. `[A3][A4]`
4. **Genelden özele.** Makro→sektör tahsis katmanı, hisse sinyallerinin ÜSTÜNE oturur (akademik olarak kanıtlı). `[A5]`
5. **Backtest gate = sistemin kalbi.** Yayınlanan getirilerin çoğu güvenilmez (look-ahead, survivorship, overfit, maliyet ihmali, rejim körlüğü). En değerli bileşen LLM zekâsı DEĞİL, sağlam robustness gate'tir. `[A6]`
6. **Veri > mimari zekâ.** Daha uzun eğitim verisi + geniş evren, mimari hünerini yener. Dar evren = overfit tuzağı. `[A7]`
7. **Model katmanlama.** Ucuz analist ajanları (Haiku) + güçlü final sentezleyici (Opus). `[A8]`
8. **Safe debate guardrail.** Ajanlar itiraz edebilir ama doğrulanabilir referansa demir atmalı — aşırı-güveni engeller. `[A9]`

---

## 1. Hedef Mimari — 4 Katman

```
┌─────────────────────────────────────────────────────────────────────┐
│ KATMAN 1 — DATA PERCEPTION (ingestion)                               │
│   • Şirket: earnings, F/K-ROE-growth, insider, earnings call         │
│   • Teknik: OHLCV, göstergeler, mum grafiği                          │
│   • Haber/Sentiment: akış + çeviri + RAG indeksi                     │
│   • Makro/Jeopolitik: faiz, enflasyon, istihdam, savaş, MB kararı    │
└───────────────────────────────┬─────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│ KATMAN 2 — REASONING ENGINE (quant + LLM hibrit)                     │
│                                                                       │
│   ▸ [YENİ] TOP-DOWN MAKRO→SEKTÖR ajanı           ◀── genelden özele  │
│      policy docs + makro + sentiment → sektör tahsisi/iştahı  [A5]   │
│                                                                       │
│   ▸ Analist ajanları (paralel):                                      │
│      fundamental · technical · sentiment · news       [A3][A4]       │
│   ▸ RAG belleği (haber/filing) + forecasting + optimizasyon  [A1]   │
└───────────────────────────────┬─────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│ KATMAN 3 — STRATEGY GENERATION                                       │
│   ▸ [YENİ] Bull vs Bear "safe debate"                 [A3][A9]       │
│   ▸ Trader sentezi → aksiyon + pozisyon boyutu                       │
│   ▸ Risk ekibi (agresif/nötr/muhafazakâr) → exposure limit  [A3]    │
└───────────────────────────────┬─────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│ KATMAN 4 — EXECUTION & CONTROL                                       │
│   ⚠️ BACKTEST/ROBUSTNESS GATE = verifier (sinyal↔emir kapısı)  [A6] │
│   ▸ Pozisyon boyutlandırma (Kelly) · kalibrasyon (Platt)            │
│   ▸ Portföy yönetimi · emir üretimi                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Mevcut Kod → Hedef Mimari Eşlemesi

Mevcut pipeline (`backend/src/finllm/pipeline/orchestrator.py`) zaten olgun bir funnel. Eşleme:

| Hedef katman | Mevcut modül | Durum |
|---|---|---|
| **K1** Data Perception | `pipeline/stage0_ingest`, `stage0b_agenda` (news), `indicators/fundamentals`, `features/technical` | ✅ Var |
| **K2** Makro→Sektör (top-down) | `pipeline/regime` (kısmî), `strategies/sector_rotation` | ⚠️ **Eksik: gerçek LLM makro→sektör katmanı** |
| **K2** Analist ajanları | `pipeline/stage1_filter`, `stage1b_setup`, `stage1c_features`, `stage2_screen`, `stage3_deep` | 🟡 Var ama tek-akış (debate yok) |
| **K2** Risk/getiri füzyonu | `indicators/risk_reward` (temel+finnhub+makro) + `signals/ranking` (birleşik öncelik) | ✅ **YENİ (2026-06-15)** — teknik+temel+earnings/analyst+makro → tek orta-vade öncelik skoru |
| **K3** Bull/Bear debate | `llm/debate.py` (adversary + judge, Sonnet 4.6) + `skills/debate-*` | ✅ **YENİ (2026-06-15)** — 2-çağrı panel, top-N adaya, ~$0.035/hisse |
| **K3** Trader sentezi + risk | `pipeline/stage4_judge`, `ensemble/multi_llm_voter`, `llm/debate` judge | ✅ Debate judge (aksiyon+güven+pozisyon boyutu+risk) |
| **K3** Orchestration | `pipeline/decision_panel` (ranking→top-N debate→hüküm) | ✅ **YENİ (2026-06-16)** — uçtan uca çalışıyor, `scripts/run_decision_panel.py` |
| **K4** Backtest gate | `pipeline/stage4_5_backtest_gate`, `backtest/engine`, `strategy_engine` | ✅ Var — **korunacak & sertleştirilecek** |
| **K4** Pozisyon/kalibrasyon | `calibration/kelly`, `calibration/platt`, `calibration/tracker` | ✅ Var |
| **K4** Writer/çıktı | `pipeline/stage5_writer` | ✅ Var |

**Özet:** Sistem %70 hazır. 3 büyük boşluk: (a) LLM makro→sektör top-down katmanı, (b) bull/bear debate, (c) backtest gate'in 5-hata'ya karşı sertleştirilmesi.

---

## 3. Referans Sistemler (örnek alınacaklar)

| Sistem | Rolü | Bizim için |
|---|---|---|
| **FinRobot** (AI4Finance) `[A2]` | Açık kaynak 4-katmanlı platform; FinGPT/FinRL ailesi | İskelet/desen referansı |
| **TradingAgents** (Tauric) `[A3]` | analist → bull/bear → trader → risk → fon yöneticisi | Karar akışı şablonu |
| **ai-hedge-fund** (virattt) `[A10]` | signal → Risk Manager → Portfolio Manager | En temiz forklanabilir kod |
| **FinDebate** `[A9]` | 5 paralel ajan + safe-debate | Guardrail deseni |
| **FinVision** `[A8]` | görüntü-tabanlı teknik ajan + model katmanlama | Teknik ajan + maliyet deseni |

> ⚠️ Hepsinin mimarisi **kendi-raporlu**; bağımsız kârlılık kanıtı YOK. Yapıyı al, sinyali kendi gate'inle doğrula. `[A2][A6][A10]`

---

## 4. Yol Haritası (faz faz)

### Faz A — Backtest gate sertleştirme ✅ **TAMAMLANDI (2026-06-15)** `[A6][A7]`
- [x] **A.1** Gerçekçi işlem maliyeti + slippage (`backtest/costs.py`, Midas tarifesi: US $1.5/işlem, BIST 0) — `--costs {midas-us,midas-bist,zero}`
- [x] **A.1** Look-ahead düzeltmesi: girişler **next-bar-OPEN** dolduruluyor (close[t]'de karar, open[t+1]'de dolum)
- [x] **A.2** Walk-forward testi (`backtest/walkforward.py`, `scripts/walkforward.py`) — çoklu kayan pencere, PF/Sharpe dağılımı + tutarlılık oranları
- [x] **A.3** Rejim etiketleme (BULL/BEAR/SIDEWAYS) + per-regime kırılım
- [x] **A.3** Robustness gate standardı (`RobustnessStandard`/`evaluate_gate`): median PF≥1.2, ≥%70 pencere PF>1, worst DD≥−30%, ≥20 işlem/pencere, bear PF≥0.9
- [x] Survivorship: delisted semboller (ör. ARM) graceful skip + loglanıyor
- **Çıktı:** Verifier-gated kapı canlı — hiçbir LLM sinyali bu gate geçmeden production'a gitmez.

> **🔴 Faz A bulgusu:** Gerçekçi maliyet + next-bar dolum + walk-forward ile strateji önce
> **rejim-bağımlı** çıktı ve gate'ten KALDI (BOĞA PF 1.28 vs AYI 0.36; %56 pencere PF>1).
>
> **🟢 Faz A.4 çözümü (2026-06-15) — gate GEÇTİ:** Kök sebep, QQQ regime gate'in (EMA21/50 +
> 20-bar eğim) 2022 bear rally'lerinde yeniden tetiklenmesiydi. Çözüm klasik **200-günlük ortalama
> (SMA200) bull/bear filtresi**: giriş için `close > SMA200` da gerekli (`qqq_uptrend(long_sma_period=200)`,
> `--regime-long-period`). Sonuç (nasdaq 2022–24, midas-us, walk-forward): **median PF 1.49, %89 pencere
> PF>1, worst DD −11.6%, AYI +4.2%.** Periyoda (200 ve 250 geçer, 150 kısa) ve setup-eşiğine (0.4/0.5)
> duyarsız → curve-fit değil. 2022-01 penceresi: 35 işlem/−16.4% → 7 işlem/−3.1% (doğru şekilde dışarıda).
> Gate mantığı da düzeltildi: sermaye korumasını ödüllendiriyor (bear getiri-bazlı ≥−5%, median işlem).
> **🟢 OOS DOĞRULANDI (2018–2021):** Canlı `pipeline/regime.py` SMA200 kuralını benimsedi. Gate rafine
> edildi (stres-temelli bear tespiti: pencere-içi benchmark DD≤−15%; tri-state: unproven≠fail). 6-aylık
> 2018–21 OOS'ta **4 stres penceresi** (2018-Q4 + COVID) yakalandı ve **GATE GEÇTİ**: bear-getiri **+14.9%**,
> worst DD −16.4%, median PF 1.24. **Sonuç: 200-DMA fix 2022'ye overfit DEĞİL — 2018/2020 bear'larına da
> genelliyor.** Bear-robustluk artık iki bağımsız dönemde (2018-Q4, COVID) kanıtlı.

### Faz B — Top-down makro→sektör katmanı ✅ **ÇEKİRDEK TAMAM (2026-06-15)** `[A5]`
- [x] **B.1** `data/macro.py` + `data/fred.py`: FRED (CPI/PCE/Fed/NFP/eğri, point-in-time) + yfinance (VIX/endeks-200DMA/altın/petrol) + RSS haber → MACRO CONTEXT. Hepsi ücretsiz.
- [x] **B.1** `llm/macro_sector.py` (Sonnet 4.6) + `skills/macro-sector-analyst`: makro context → risk stance + 12 sektör iştahı (0-1). Haberlerle keskin (Tech 0.78/Energy 0.30, Iran-deal muhakemesi), veri zayıfsa neutral.
- [x] **B.2** `portfolio/sector_gate.py`: weight/filter/veto/off modları. Sektör verisi evrenden (Ticker.sector). 16/16 test.
- [x] **B.3** Backtest entegrasyonu (`strategy_engine` macro_provider, aylık-cache) + `scripts/measure_macro_lift.py` lift ölçümü.

> **🟢 Faz B lift bulgusu (nasdaq 2022-24, gerçek Sonnet, $0.41):** **veto modu kazandırıyor** —
> +48.3% vs off +43.4%, Sharpe 0.89 vs 0.82 (+0.07), PF 1.42 vs 1.37, daha az işlem (244 vs 251),
> aynı DD. weight ~etkisiz, filter +0.02. **Uyarılar:** lift tek risk_off ayından (küçük örneklem),
> 200-DMA regime gate ile örtüşüyor, ve backtest CANLI değeri AZ gösteriyor (tarihsel haber yok →
> 18/23 ay neutral). **Karar:** veto modu opsiyonel adopte; asıl değer canlı (haber-tahrikli rotasyon)
> + geniş çok-sektörlü evren. **Sektör→hisse kapılama açık sorusu ÇÖZÜLDÜ: weight/filter/veto hepsi
> implement + configurable; veto en iyi.**

### Faz C — Multi-agent debate `[A3][A9]`
- [ ] Analist ajanlarını paralelleştir (fundamental/technical/sentiment/news)
- [ ] Bull vs Bear safe-debate (referansa demir atma zorunlu)
- [ ] Trader sentezi + 3-yönlü risk ekibi → exposure limit

### Faz D — Model katmanlama & maliyet `[A8]`
- [ ] Ucuz analistler (Haiku) + güçlü final sentez (Opus)
- [ ] 3 piyasa × 5-7 ajan per-hisse maliyet/gecikme ölçümü (açık soru)
- [ ] Not: Opus temperature deprecated — literal değil, *katmanlama fikrini* uygula

### Faz E — BIST & Altın genişlemesi
- [ ] Türkçe haber/sentiment modeli + veri sağlayıcı
- [ ] Makro→sektör deseninin ince, perakende-ağırlıklı BIST'e transferini test et

---

## 5. Açık Sorular (kapatılacak)

1. **Sektör→hisse kapılama:** Makro/sektör çıktısı Stage1+Stage1B+QQQ'yu nasıl etkileyecek — sert filtre, güven ağırlığı, yoksa veto? `[A5]`
2. **BIST veri & dil:** Hangi sağlayıcı + Türkçe sentiment modeli? Desen ince piyasaya transfer olur mu?
3. **Maliyet/gecikme:** 3 piyasada 5-7 ajanlı per-hisse analizin gerçek API maliyeti? En ucuz "yeterli" Claude katmanı?
4. **Gate standardı:** 5 değerlendirme hatasını önlemek için min. backtest penceresi/evren/maliyet modeli? `[A6]`

## 6. Çürütülen İddia (tasarımda kullanma)
- ❌ "Koordinasyon protokolü, model seçiminden önemlidir" hipotezi çekişmeli doğrulamada **0-3 reddedildi.** Bunun üstüne tasarım kurma. `[A6]`

---

## Kaynaklar

- **[A1]** Gong (UCL, FinTech 2026) — 4-katmanlı mimari, "no single model type is sufficient" — arXiv:2603.13942 / DOI 10.3390/fintech5020034
- **[A2]** FinRobot (AI4Finance) — açık kaynak 4-katmanlı ajan platformu — arXiv:2405.14767 · github.com/AI4Finance-Foundation/FinRobot
- **[A3]** TradingAgents (Tauric) — rol-tabanlı trading firması, bull/bear + risk ekibi — arXiv:2412.20138 · github.com/TauricResearch/TradingAgents
- **[A4]** FinDebate — 5 paralel uzman ajan — arXiv:2509.17395 (FinNLP@EMNLP 2025)
- **[A5]** Top-Down Sector Allocation w/ LLMs — makro→sektör tahsisi — arXiv:2503.09647 (ICLR 2025)
- **[A6]** LLM Trading Reliability Survey (Georgia Tech/Adobe) — 5 değerlendirme hatası — arXiv:2603.27539v1 (FINSABER arXiv:2505.07078)
- **[A7]** FinVision değerlendirme kırılganlığı (dar evren overfit) — arXiv:2411.08899 (ACM ICAIF 2024)
- **[A8]** FinVision model katmanlama (ucuz analist + güçlü reasoner) — arXiv:2411.08899
- **[A9]** FinDebate "safe debate" protokolü — arXiv:2509.17395
- **[A10]** ai-hedge-fund (virattt) — signal→risk→portfolio şablonu — github.com/virattt/ai-hedge-fund

> Tüm getiri rakamları (Sharpe 2.51, %23.26 vb.) güvenilmezdir `[A6]` — yön gösterici, hedef değil.
> Hiçbir referans sistem BIST veya Altın'ı kapsamıyor; makro paper sektör seviyesinde durur (tek-hisse zincirini kanıtlamaz).
