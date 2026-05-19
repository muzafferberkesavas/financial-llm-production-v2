"use client";

import Link from "next/link";
import { motion } from "framer-motion";

export function CTA() {
  return (
    <section className="relative py-32 px-6 overflow-hidden">
      <div className="absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/10 via-violet-500/10 to-transparent" />
        <div
          className="absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(circle at 50% 50%, rgba(34,211,238,0.15), transparent 50%)",
          }}
        />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.6 }}
        className="relative mx-auto max-w-4xl text-center"
      >
        <div className="font-mono text-[11px] tracking-[0.3em] text-cyan-300/80">
          BAŞLAMAYA HAZIR MISINIZ
        </div>
        <h2 className="mt-3 text-5xl md:text-6xl font-bold tracking-tight">
          <span className="text-zinc-100">Sinyalleri</span>{" "}
          <span className="bg-gradient-to-br from-cyan-300 via-cyan-400 to-violet-400 bg-clip-text text-transparent">
            şimdi inceleyin.
          </span>
        </h2>
        <p className="mt-6 text-lg text-zinc-400 leading-relaxed max-w-2xl mx-auto">
          FinLLM her gün NASDAQ açılış öncesi ve BIST seans başlangıcında
          otomatik olarak çalışır. Telegram kanalına katılın, panelden anlık
          kararları takip edin.
        </p>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Link
            href="/app/signals"
            className="group inline-flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-violet-500 hover:from-cyan-400 hover:to-violet-400 text-white px-8 py-4 rounded-md font-medium shadow-2xl shadow-cyan-500/30 transition text-base"
          >
            Paneli Aç
            <span className="transition group-hover:translate-x-1">→</span>
          </Link>
          <Link
            href="https://t.me/finllm_signals"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 border border-zinc-700 hover:border-zinc-500 text-zinc-300 hover:text-white px-8 py-4 rounded-md font-medium transition text-base"
          >
            <svg
              className="w-4 h-4"
              viewBox="0 0 24 24"
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z" />
            </svg>
            Telegram Kanalı
          </Link>
        </div>

        <div className="mt-12 flex items-center justify-center gap-2 text-xs font-mono text-zinc-500">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
          <span>
            Bu sistem yatırım tavsiyesi vermez; yalnızca araştırma amaçlıdır.
          </span>
        </div>
      </motion.div>
    </section>
  );
}
