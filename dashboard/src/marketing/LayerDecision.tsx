"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

type Layer = {
  id: string;
  title: string;
  short: string;
  detail: string;
  example: string;
  accent: string;
};

const LAYERS: Layer[] = [
  {
    id: "K0",
    title: "Piyasa Gündemi",
    short: "Haber akışı yapılandırılmış özet olarak süzülür",
    detail:
      "RSS, SEC EDGAR (8-K, 10-Q), Finnhub ve KAP akışları Claude Haiku ile yapılandırılmış on başlıklı İngilizce gündeme dönüşür. Ham haber asla derin analiste gitmez; üç katmanlı güvensiz-girdi izolasyonu uygulanır.",
    example:
      "BURRY · S&P YOĞUNLAŞMA UYARISI · duygu skoru: -0.08 · semboller: [QQQ, MAGS]",
    accent: "cyan",
  },
  {
    id: "K1",
    title: "Piyasa Rejimi Filtresi",
    short: "VIX güvenlik kesicisi ve makro rejim tespiti",
    detail:
      "VIX 35 üzerinde ya da SPY 5 günlük getirisi -%4 altında ise işlem askıya alınır. Kalan günlerde sakin / korku / coşku rejimi tüm pozisyon büyüklüklerini ayarlar.",
    example: "VIX=18,2 · sakin · SPY 5g=+0,3% · 200g üstünde=evet → İŞLEM SERBEST",
    accent: "violet",
  },
  {
    id: "K2",
    title: "Çoklu Zaman Dilimi Trendi",
    short: "Haftalık + günlük + saatlik hizalama",
    detail:
      "Haftalık EMA50/200 sıralaması, günlük altın/ölüm kesişimi ve saatlik momentum birlikte değerlendirilir. Üç dilim aynı yöne işaret etmiyorsa kurulum zayıf sayılır.",
    example:
      "HAFTALIK YÜKSELİŞ + GÜNLÜK ALTIN KESİŞİM + SAATLİK ALICI = GÜÇLÜ TREND",
    accent: "emerald",
  },
  {
    id: "K3",
    title: "Kurulum + Bileşke Skoru",
    short: "Sekiz bileşenli teknik bileşke ve strateji topluluğu",
    detail:
      "EMA'ya geri çekiliş, boğa bayrağı, kırılım, bilanço sonrası seyir, sektör rotasyonu. Trend, momentum, hacim, volatilite, formasyon, destek/direnç, çoklu zaman dilimi ve uyumsuzluk birleşerek 0-100 skor üretir.",
    example: "QCOM · geri-çekiliş_ema 0,86 · bileşke 76 · GÜÇLÜ TREND",
    accent: "amber",
  },
  {
    id: "K4",
    title: "Hacim ve Emir Akışı",
    short: "Kurumsal aktivite teyidi",
    detail:
      "OBV yönü ve uyumsuzluk, hacim kuruması sonrası tepki, 50 günlük medyana göre göreli hacim. Yalın fiyat hareketine güvenilmez; kurumsal teyit aranır.",
    example:
      "Tepki hacmi medyanın 1,4 katı · OBV pozitif · kırılım öncesi birikim",
    accent: "rose",
  },
  {
    id: "K5",
    title: "Risk Haritası",
    short: "Zarar durdur, hedef ve uyarı bayrakları",
    detail:
      "Salınım dibi ve ATR ile zarar durdur; Fibonacci genişlemesi ve sektör profilinden hedef. RSI_AŞIRI_ALIM, SALINIM_TEPESİNE_YAKIN, BİLANÇO_YAKLAŞIYOR, OBV_NEGATİF_UYUMSUZLUK — her bayrak güveni sınırlar.",
    example:
      "Zarar durdur 182 $ (-%3,8) · Hedef 215 $ (+%13,6) · bayraklar: [RSI_AŞIRI_ALIM]",
    accent: "fuchsia",
  },
  {
    id: "K6",
    title: "Temel Analiz",
    short: "F/K, ROE, büyüme ve sektör medyanı",
    detail:
      "Yahoo Finance verisinden yirmi alan. Değer (40) + Kalite (30) + Büyüme (30) = 100. Sektör medyanı ile karşılaştırma; PAHALI_ÇARPAN ve BİLANÇO_YAKLAŞIYOR (T-5 gün) bayrakları otomatik oluşur.",
    example:
      "NVDA · F/K 45 · ROE %101 · Net Kâr Marjı %56 · Gelir yıllık +%73",
    accent: "blue",
  },
  {
    id: "K7",
    title: "Kalibre Karar",
    short: "Platt ölçeklemesi ve Kelly büyüklüğü",
    detail:
      "Yapay zekanın ham güveni, geçmiş sonuçlar üzerinden eğitilen Platt ölçeklemesi ile gerçek isabet oranına eşlenir. Pozisyon büyüklüğü Kelly oranı ile belirlenir: f* = (p·b − q) / b. Çoklu teyit eşiği ve kaynaksız ifade düşürmesi son katmanda uygulanır.",
    example: "AL · ham 0,74 → kalibre 0,62 → Kelly 2.265 $ (%22,7)",
    accent: "amber",
  },
];

const ACCENTS: Record<
  string,
  { dot: string; text: string; bg: string; ring: string }
> = {
  cyan: {
    dot: "bg-cyan-400 shadow-cyan-400/50",
    text: "text-cyan-300",
    bg: "from-cyan-500/15",
    ring: "border-cyan-500/30",
  },
  violet: {
    dot: "bg-violet-400 shadow-violet-400/50",
    text: "text-violet-300",
    bg: "from-violet-500/15",
    ring: "border-violet-500/30",
  },
  emerald: {
    dot: "bg-emerald-400 shadow-emerald-400/50",
    text: "text-emerald-300",
    bg: "from-emerald-500/15",
    ring: "border-emerald-500/30",
  },
  amber: {
    dot: "bg-amber-400 shadow-amber-400/50",
    text: "text-amber-300",
    bg: "from-amber-500/15",
    ring: "border-amber-500/30",
  },
  rose: {
    dot: "bg-rose-400 shadow-rose-400/50",
    text: "text-rose-300",
    bg: "from-rose-500/15",
    ring: "border-rose-500/30",
  },
  fuchsia: {
    dot: "bg-fuchsia-400 shadow-fuchsia-400/50",
    text: "text-fuchsia-300",
    bg: "from-fuchsia-500/15",
    ring: "border-fuchsia-500/30",
  },
  blue: {
    dot: "bg-blue-400 shadow-blue-400/50",
    text: "text-blue-300",
    bg: "from-blue-500/15",
    ring: "border-blue-500/30",
  },
};

export function LayerDecision() {
  const [active, setActive] = useState<string>(LAYERS[0].id);
  const current = LAYERS.find((l) => l.id === active) ?? LAYERS[0];
  const a = ACCENTS[current.accent];

  return (
    <section className="relative py-32 px-6 border-t border-zinc-900 overflow-hidden">
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-1/3 right-1/3 w-[600px] h-[600px] bg-violet-500/10 rounded-full blur-[140px]" />
      </div>

      <div className="mx-auto max-w-7xl">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="mb-16 max-w-2xl"
        >
          <div className="font-mono text-[11px] tracking-[0.3em] text-amber-300/80">
            KARAR KATMANLARI
          </div>
          <h2 className="mt-3 text-4xl md:text-5xl font-bold tracking-tight text-zinc-100">
            Yedi katmanlı karar mimarisi
          </h2>
          <p className="mt-5 text-zinc-400 text-lg leading-relaxed">
            Her sinyalin yedi ayrı kaynaktan onay alması gerekir. Tek bir
            göstergeye ya da tek bir yapay zeka cümlesine güvenmeyiz. Aşağıdaki
            katmanlara dokunup içeride neyin döndüğünü inceleyebilirsiniz.
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-[320px_1fr] gap-6 lg:gap-10">
          <div className="flex lg:flex-col gap-1.5 overflow-x-auto lg:overflow-visible pb-2 lg:pb-0 -mx-6 px-6 lg:mx-0 lg:px-0">
            {LAYERS.map((l, i) => {
              const la = ACCENTS[l.accent];
              const isActive = active === l.id;
              return (
                <motion.button
                  key={l.id}
                  onClick={() => setActive(l.id)}
                  onMouseEnter={() => setActive(l.id)}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: i * 0.05 }}
                  className={`relative flex-shrink-0 lg:flex-shrink text-left rounded-lg border transition-all px-4 py-3 ${
                    isActive
                      ? `${la.ring} bg-zinc-900/80`
                      : "border-zinc-900 bg-zinc-950/40 hover:border-zinc-800"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`w-2 h-2 rounded-full shadow-md transition-all ${
                        isActive ? `${la.dot} scale-125` : "bg-zinc-700"
                      }`}
                    />
                    <span
                      className={`font-mono text-[10px] tracking-[0.2em] ${
                        isActive ? la.text : "text-zinc-500"
                      }`}
                    >
                      {l.id}
                    </span>
                    <span
                      className={`text-sm font-medium whitespace-nowrap lg:whitespace-normal ${
                        isActive ? "text-zinc-100" : "text-zinc-400"
                      }`}
                    >
                      {l.title}
                    </span>
                  </div>
                  {isActive && (
                    <motion.div
                      layoutId="layer-bar"
                      className={`absolute left-0 top-0 bottom-0 w-0.5 rounded-r ${la.dot}`}
                      transition={{ type: "spring", stiffness: 400, damping: 35 }}
                    />
                  )}
                </motion.button>
              );
            })}
          </div>

          <div className="relative rounded-2xl border border-zinc-800 bg-zinc-950/60 backdrop-blur overflow-hidden min-h-[440px]">
            <div
              className={`absolute inset-0 -z-10 bg-gradient-to-br ${a.bg} via-transparent to-transparent opacity-70 transition-opacity duration-700`}
            />

            <AnimatePresence mode="wait">
              <motion.div
                key={current.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.35 }}
                className="p-8 md:p-12"
              >
                <div className="flex items-center gap-3 mb-6">
                  <span className={`w-3 h-3 rounded-full shadow-lg ${a.dot}`} />
                  <span className={`font-mono text-xs tracking-[0.3em] ${a.text}`}>
                    KATMAN {current.id}
                  </span>
                </div>

                <h3 className="text-3xl md:text-4xl font-bold tracking-tight text-zinc-100">
                  {current.title}
                </h3>
                <p className={`mt-2 text-lg font-medium ${a.text}`}>
                  {current.short}
                </p>

                <p className="mt-8 text-zinc-300 leading-relaxed max-w-2xl">
                  {current.detail}
                </p>

                <div className="mt-10">
                  <div className="font-mono text-[10px] tracking-[0.3em] text-zinc-500 mb-2">
                    CANLI ÖRNEK
                  </div>
                  <div
                    className={`rounded-lg border ${a.ring} bg-zinc-950/80 px-5 py-4 font-mono text-sm text-zinc-200`}
                  >
                    {current.example}
                  </div>
                </div>

                <div className="mt-10 flex items-center gap-3 text-xs font-mono text-zinc-500">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span>
                    Tüm katmanları geçen aday, derin analist katmanına çıkar
                  </span>
                </div>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}
