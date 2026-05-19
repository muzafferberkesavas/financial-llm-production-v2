"use client";

import { motion, useInView, useMotionValue, useTransform, animate } from "framer-motion";
import { useEffect, useRef } from "react";

const STATS = [
  {
    label: "Veri kaynağı",
    value: 5,
    suffix: "+",
    subtitle: "Yahoo · SEC · Finnhub · RSS · KAP",
  },
  {
    label: "Sembol evreni",
    value: 600,
    suffix: "+",
    subtitle: "NASDAQ + BIST + emtia",
  },
  {
    label: "Karar katmanı",
    value: 7,
    subtitle: "Haber → Rejim → ÇZD → Trend → Hacim → Risk → Temel",
  },
  {
    label: "Teknik gösterge",
    value: 30,
    suffix: "+",
    subtitle: "RSI · MACD · BB · ADX · OBV · Fib · Ichimoku · Supertrend",
  },
  {
    label: "Aktif strateji",
    value: 3,
    subtitle: "EMA geri çekilişi · bilanço sonrası seyir · sektör rotasyonu",
  },
  {
    label: "Tur başına maliyet",
    value: 3,
    suffix: "-5 $",
    subtitle: "15 sembol · önbellekli LLM çağrıları",
  },
];

function AnimatedCounter({ to }: { to: number }) {
  const count = useMotionValue(0);
  const rounded = useTransform(count, (v) => Math.round(v).toString());
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-50px" });

  useEffect(() => {
    if (!inView) return;
    const controls = animate(count, to, { duration: 1.6, ease: "easeOut" });
    return () => controls.stop();
  }, [inView, count, to]);

  useEffect(() => {
    return rounded.on("change", (v) => {
      if (ref.current) ref.current.textContent = v;
    });
  }, [rounded]);

  return <span ref={ref}>0</span>;
}

export function Stats() {
  return (
    <section className="relative py-32 px-6 border-t border-zinc-900">
      <div className="mx-auto max-w-7xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="mb-12 text-center"
        >
          <div className="font-mono text-[11px] tracking-[0.3em] text-zinc-500">
            RAKAMLARLA
          </div>
          <h2 className="mt-3 text-3xl md:text-4xl font-bold tracking-tight text-zinc-100">
            FinLLM'in ölçeği
          </h2>
        </motion.div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-px bg-zinc-900 rounded-2xl overflow-hidden border border-zinc-800">
          {STATS.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.05 }}
              className="bg-zinc-950 p-8"
            >
              <div className="font-mono text-[10px] tracking-[0.3em] text-zinc-500 uppercase">
                {stat.label}
              </div>
              <div className="mt-2 flex items-baseline">
                <span className="text-5xl font-bold tracking-tight bg-gradient-to-br from-zinc-100 to-zinc-400 bg-clip-text text-transparent tabular-nums">
                  <AnimatedCounter to={stat.value} />
                </span>
                {stat.suffix && (
                  <span className="text-3xl font-bold text-zinc-500 ml-1">
                    {stat.suffix}
                  </span>
                )}
              </div>
              <div className="mt-3 text-xs text-zinc-500 leading-relaxed">
                {stat.subtitle}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
