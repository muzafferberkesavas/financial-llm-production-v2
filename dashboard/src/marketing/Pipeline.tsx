"use client";

import { motion } from "framer-motion";

const STAGES = [
  {
    id: "0",
    label: "Veri Toplama",
    desc: "Yahoo Finance + Finnhub + SEC EDGAR + RSS akışları + KAP",
    metric: "62-500 hisse",
    color: "from-zinc-500 to-zinc-400",
  },
  {
    id: "0B",
    label: "Piyasa Gündemi",
    desc: "Claude Haiku · 10 başlıkta yapılandırılmış İngilizce özet",
    metric: "≈ 0,006 $",
    color: "from-zinc-400 to-cyan-400",
  },
  {
    id: "1",
    label: "Sert Eleme",
    desc: "Fiyat, piyasa değeri, hacim ve EMA eşiklerinde ön eleme",
    metric: "≈ %75 elenir",
    color: "from-cyan-400 to-cyan-500",
  },
  {
    id: "1B",
    label: "Kurulum Tespiti",
    desc: "Geri çekiliş, boğa bayrağı, kırılım, bilanço sonrası seyir, sektör rotasyonu",
    metric: "3 strateji",
    color: "from-cyan-500 to-blue-500",
  },
  {
    id: "1C",
    label: "Bileşke Skoru",
    desc: "Sekiz bileşenli teknik bileşke + yüz puanlık temel skor",
    metric: "0-100",
    color: "from-blue-500 to-violet-500",
  },
  {
    id: "2",
    label: "Ön Eleme (LLM)",
    desc: "Haiku · güçlü / izle / ele kategorize eder",
    metric: "≈ 0,001 $ / hisse",
    color: "from-violet-500 to-violet-600",
  },
  {
    id: "3",
    label: "Derin Analiz",
    desc: "Claude Opus 4.7 · yedi katmanlı analist gerekçesi",
    metric: "≈ 0,20 $ / hisse",
    color: "from-violet-600 to-fuchsia-500",
  },
  {
    id: "4",
    label: "Meta-Yargı",
    desc: "Çoklu teyit + Kelly büyüklüğü + kaynaksız ifade düşürmesi",
    metric: "Tahsis",
    color: "from-fuchsia-500 to-pink-500",
  },
  {
    id: "4.5",
    label: "Geriye Dönük Test Kapısı",
    desc: "Son 30 günde kağıt-üzeri sınama + işlem maliyetleri dahil",
    metric: "İsabet > %40",
    color: "from-pink-500 to-rose-500",
  },
  {
    id: "5",
    label: "Yayın + Uyarı",
    desc: "Postgres + Telegram + WebSocket + Push bildirim",
    metric: "Gerçek zamanlı",
    color: "from-rose-500 to-amber-500",
  },
];

export function Pipeline() {
  return (
    <section className="relative py-32 px-6 border-t border-zinc-900">
      <div className="mx-auto max-w-7xl">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="mb-16"
        >
          <div className="font-mono text-[11px] tracking-[0.3em] text-violet-300/80">
            SÜREÇ MİMARİSİ
          </div>
          <h2 className="mt-3 text-4xl md:text-5xl font-bold tracking-tight text-zinc-100">
            On aşamalı süzgeç
          </h2>
          <p className="mt-5 text-zinc-400 max-w-2xl text-lg leading-relaxed">
            Beş yüz hisseyi büyük dil modeline atmak yerine; kantitatif ön
            eleme, ucuz model ile ön tarama, pahalı model ile derin analiz
            ve Kelly tabanlı tahsis. Her aday, sinyale dönüşmeden önce on
            kapıdan geçer.
          </p>
        </motion.div>

        <div className="relative">
          <div className="absolute left-6 top-0 bottom-0 w-px bg-gradient-to-b from-zinc-700 via-zinc-800 to-transparent md:left-1/2 md:-translate-x-1/2" />

          <div className="space-y-6">
            {STAGES.map((stage, i) => (
              <motion.div
                key={stage.id}
                initial={{ opacity: 0, x: i % 2 === 0 ? -30 : 30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.5, delay: i * 0.05 }}
                className={`relative flex items-center gap-6 md:gap-12 ${
                  i % 2 === 0 ? "md:flex-row" : "md:flex-row-reverse"
                }`}
              >
                <div className="relative z-10 flex-shrink-0">
                  <div
                    className={`relative w-12 h-12 rounded-lg bg-gradient-to-br ${stage.color} p-[1px]`}
                  >
                    <div className="w-full h-full rounded-lg bg-zinc-950 flex items-center justify-center font-mono text-xs font-bold text-white">
                      {stage.id}
                    </div>
                  </div>
                </div>

                <div className="flex-1 md:max-w-md rounded-lg border border-zinc-800 bg-zinc-950/40 px-5 py-4 backdrop-blur">
                  <div className="flex items-baseline justify-between gap-4">
                    <div className="font-semibold text-zinc-100">
                      {stage.label}
                    </div>
                    <div className="font-mono text-[11px] text-zinc-500 tracking-wider">
                      {stage.metric}
                    </div>
                  </div>
                  <div className="mt-1 text-sm text-zinc-400">{stage.desc}</div>
                </div>

                <div className="hidden md:block flex-1" />
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
