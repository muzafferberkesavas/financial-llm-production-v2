"use client";

import { motion } from "framer-motion";

const PILLARS = [
  {
    code: "01",
    title: "Çift Pazar Mimarisi",
    body: "BIST ve NASDAQ aynı süreçten geçer; piyasaya özgü eşikler, takas kuralları (T+1 / T+2) ve maliyet yapıları (BSMV, komisyon) otomatik olarak uygulanır.",
    accent: "cyan",
    icon: "globe",
  },
  {
    code: "02",
    title: "Yapay Zeka Karar Mimarisi",
    body: "Claude Opus 4.7 ile yapılandırılmış araç çağrısı, yedi katmanlı analist mantığı ve önek-önbellek yapısı. Her sayı kaynağına işaretli.",
    accent: "violet",
    icon: "brain",
  },
  {
    code: "03",
    title: "Temel + Teknik Birleşimi",
    body: "Otuz teknik gösterge, sekiz bileşenli bileşke skoru ve yirminin üzerinde temel veri alanı. Değer, kalite ve büyüme tek bir yüz puanlık ölçekte birleştirilir.",
    accent: "emerald",
    icon: "balance",
  },
  {
    code: "04",
    title: "Kalibre Edilmiş Güven",
    body: "Yapay zekanın ham güveni, geçmiş sonuçlar üzerinden Platt ölçeklemesi ile gerçek isabet oranına eşlenir. Pozisyon büyüklüğü Kelly kriteri ile belirlenir.",
    accent: "amber",
    icon: "shield",
  },
];

const ACCENT_CLASSES: Record<string, string> = {
  cyan: "text-cyan-300/80 from-cyan-500/40 via-cyan-500/40",
  violet: "text-violet-300/80 from-violet-500/40 via-violet-500/40",
  emerald: "text-emerald-300/80 from-emerald-500/40 via-emerald-500/40",
  amber: "text-amber-300/80 from-amber-500/40 via-amber-500/40",
};

const CHIP: Record<string, string> = {
  cyan: "bg-cyan-500/10 text-cyan-300 ring-cyan-500/20",
  violet: "bg-violet-500/10 text-violet-300 ring-violet-500/20",
  emerald: "bg-emerald-500/10 text-emerald-300 ring-emerald-500/20",
  amber: "bg-amber-500/10 text-amber-300 ring-amber-500/20",
};

function PillarIcon({ name, className }: { name: string; className?: string }) {
  const common = {
    className,
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round",
    strokeLinejoin: "round",
  } as const;
  if (name === "globe") {
    return (
      <svg viewBox="0 0 24 24" {...common}>
        <circle cx="12" cy="12" r="9" />
        <path d="M3 12h18" />
        <path d="M12 3a14 14 0 0 1 0 18" />
        <path d="M12 3a14 14 0 0 0 0 18" />
      </svg>
    );
  }
  if (name === "brain") {
    return (
      <svg viewBox="0 0 24 24" {...common}>
        <path d="M9 6a3 3 0 0 0-3 3v1a3 3 0 0 0-2 5 3 3 0 0 0 2 5v1a3 3 0 0 0 3 3" />
        <path d="M15 6a3 3 0 0 1 3 3v1a3 3 0 0 1 2 5 3 3 0 0 1-2 5v1a3 3 0 0 1-3 3" />
        <path d="M12 6v15" />
      </svg>
    );
  }
  if (name === "balance") {
    return (
      <svg viewBox="0 0 24 24" {...common}>
        <path d="M12 4v17" />
        <path d="M6 8l-3 6h6z" />
        <path d="M18 8l3 6h-6z" />
        <path d="M3 14a3 3 0 0 0 6 0" />
        <path d="M15 14a3 3 0 0 0 6 0" />
        <path d="M6 21h12" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" {...common}>
      <path d="M12 3l8 4v5c0 5-3.5 8.5-8 9-4.5-.5-8-4-8-9V7z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

export function Pillars() {
  return (
    <section className="relative py-32 px-6">
      <div className="mx-auto max-w-7xl">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="mb-16"
        >
          <div className="font-mono text-[11px] tracking-[0.3em] text-cyan-300/80">
            PLATFORM
          </div>
          <h2 className="mt-3 text-4xl md:text-5xl font-bold tracking-tight text-zinc-100 max-w-2xl">
            Kurumsal düzey bir sinyal mimarisi
          </h2>
          <p className="mt-5 text-zinc-400 max-w-2xl text-lg leading-relaxed">
            Anthropic finansal hizmetler örüntüleri, akademik kantitatif
            altyapı ve disiplinli risk yönetimi — her parçası ölçülmüş,
            her sinyal kaynağına işaretli.
          </p>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {PILLARS.map((p, i) => {
            const accent = ACCENT_CLASSES[p.accent] || ACCENT_CLASSES.cyan;
            return (
              <motion.div
                key={p.code}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                whileHover={{ y: -4 }}
                className="group relative rounded-xl border border-zinc-800 bg-zinc-950/60 p-6 backdrop-blur transition-all hover:border-zinc-700"
              >
                <div
                  className={`inline-flex items-center justify-center w-11 h-11 rounded-lg ring-1 ${CHIP[p.accent]} mb-4`}
                >
                  <PillarIcon name={p.icon} className="w-5 h-5" />
                </div>
                <div className={`font-mono text-[11px] tracking-[0.3em] ${accent.split(" ")[0]} mb-2`}>
                  {p.code}
                </div>
                <div className="font-bold text-xl text-white">{p.title}</div>
                <p className="mt-3 text-zinc-400 text-sm leading-relaxed">
                  {p.body}
                </p>
                <div
                  className={`mt-6 h-px bg-gradient-to-r ${accent.split(" ").slice(1).join(" ")} to-transparent`}
                />
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
