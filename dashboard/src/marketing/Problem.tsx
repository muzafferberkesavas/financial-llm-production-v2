"use client";

import { motion } from "framer-motion";

const COLUMNS = [
  {
    code: "01",
    title: "Klasik Teknik Tarayıcılar",
    subtitle: "TradingView, Investing, Bloomberg eşikleri",
    accent: "rose",
    points: [
      { kind: "bad", text: "Sayısal gösterge filtreleri; bağlam ve haber yok" },
      { kind: "bad", text: "Yüzlerce hisseyi tek tek manuel taramak gerekir" },
      { kind: "bad", text: "Bilanço ve makro takvim sürece dahil değildir" },
      { kind: "bad", text: "Olasılık kalibrasyonu ya da risk modeli yoktur" },
    ],
  },
  {
    code: "02",
    title: "Düz Yapay Zeka Sohbetleri",
    subtitle: "ChatGPT, Gemini ve benzeri genel modeller",
    accent: "amber",
    points: [
      { kind: "bad", text: "Halüsinasyon riski yüksek — uydurma sayılar" },
      { kind: "bad", text: "Gerçek zamanlı piyasa verisine erişim sınırlı" },
      { kind: "bad", text: "Pozisyon büyüklüğü hesabı yapılmaz" },
      { kind: "bad", text: "Geriye dönük test kapısı bulunmaz" },
    ],
  },
  {
    code: "03",
    title: "FinLLM",
    subtitle: "Kantitatif ön eleme + büyük dil modeli + kalibrasyon",
    accent: "cyan",
    highlight: true,
    points: [
      { kind: "good", text: "Önce nicel ön eleme, sonra yapay zeka derin analizi" },
      { kind: "good", text: "Her sayı kaynağa bağlı — tool-calling ile doğrulama" },
      { kind: "good", text: "Platt kalibrasyonu + Kelly kriteri ile pozisyon boyu" },
      { kind: "good", text: "Otuz günlük kağıt-üzeri test + VIX güvenlik kesicisi" },
    ],
  },
];

const ACCENT: Record<string, { ring: string; text: string; glow: string }> = {
  rose: {
    ring: "border-rose-900/40",
    text: "text-rose-300/80",
    glow: "from-rose-500/10",
  },
  amber: {
    ring: "border-amber-900/40",
    text: "text-amber-300/80",
    glow: "from-amber-500/10",
  },
  cyan: {
    ring: "border-cyan-500/50",
    text: "text-cyan-300",
    glow: "from-cyan-500/20",
  },
};

export function Problem() {
  return (
    <section className="relative py-32 px-6 border-t border-zinc-900 overflow-hidden">
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-cyan-500/5 blur-[120px] rounded-full" />
      </div>

      <div className="mx-auto max-w-7xl">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="mb-16 text-center max-w-3xl mx-auto"
        >
          <div className="font-mono text-[11px] tracking-[0.3em] text-rose-300/80">
            MEVCUT ARAÇLARIN BOŞLUĞU
          </div>
          <h2 className="mt-3 text-4xl md:text-5xl font-bold tracking-tight text-zinc-100">
            Neden mevcut araçlar yetmiyor?
          </h2>
          <p className="mt-5 text-zinc-400 text-lg leading-relaxed">
            Sermaye piyasası ne yalnızca kuru göstergelerle ne de
            doğrulanmamış yapay zeka çıktısıyla çözülebilir. Üstünlük, iki
            yaklaşımın disipline edilmiş birleşiminden doğar.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-4 md:gap-6">
          {COLUMNS.map((col, i) => {
            const a = ACCENT[col.accent];
            return (
              <motion.div
                key={col.code}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.5, delay: i * 0.12 }}
                className={`relative rounded-2xl border ${a.ring} bg-zinc-950/60 backdrop-blur p-7 ${
                  col.highlight
                    ? "md:-translate-y-3 shadow-2xl shadow-cyan-500/10"
                    : ""
                }`}
              >
                <div
                  className={`absolute inset-0 -z-10 rounded-2xl bg-gradient-to-b ${a.glow} to-transparent opacity-60`}
                />

                <div className="flex items-center justify-between mb-5">
                  <div className={`font-mono text-[10px] tracking-[0.3em] ${a.text}`}>
                    YAKLAŞIM · {col.code}
                  </div>
                  {col.highlight && (
                    <span className="font-mono text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                      BİZ
                    </span>
                  )}
                </div>

                <h3 className="text-2xl font-bold text-zinc-100 mb-1">
                  {col.title}
                </h3>
                <p className="text-sm text-zinc-500 mb-6">{col.subtitle}</p>

                <ul className="space-y-3">
                  {col.points.map((p, idx) => (
                    <motion.li
                      key={p.text}
                      initial={{ opacity: 0, x: -10 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.3, delay: i * 0.12 + idx * 0.08 }}
                      className="flex items-start gap-3 text-sm"
                    >
                      <span
                        className={`mt-0.5 flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold ${
                          p.kind === "good"
                            ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                            : "bg-rose-500/10 text-rose-400/80 border border-rose-500/20"
                        }`}
                      >
                        {p.kind === "good" ? "✓" : "✕"}
                      </span>
                      <span
                        className={
                          p.kind === "good" ? "text-zinc-200" : "text-zinc-500"
                        }
                      >
                        {p.text}
                      </span>
                    </motion.li>
                  ))}
                </ul>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
