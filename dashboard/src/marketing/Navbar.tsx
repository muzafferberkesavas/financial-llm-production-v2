"use client";

import Link from "next/link";
import { motion, useScroll, useTransform } from "framer-motion";

export function MarketingNavbar() {
  const { scrollY } = useScroll();
  const bg = useTransform(scrollY, [0, 80], ["rgba(0,0,0,0)", "rgba(0,0,0,0.7)"]);
  const border = useTransform(
    scrollY,
    [0, 80],
    ["rgba(255,255,255,0)", "rgba(63,63,70,0.4)"],
  );

  return (
    <motion.header
      style={{ backgroundColor: bg, borderColor: border }}
      className="fixed top-0 z-50 w-full backdrop-blur-md border-b transition-all"
    >
      <div className="mx-auto max-w-7xl px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 group">
          <motion.div
            className="relative w-8 h-8"
            whileHover={{ rotate: 90 }}
            transition={{ duration: 0.3 }}
          >
            <div className="absolute inset-0 bg-gradient-to-br from-cyan-400 to-violet-500 rounded" />
            <div className="absolute inset-[2px] bg-black rounded-[2px] flex items-center justify-center font-mono text-xs font-bold">
              ƒ
            </div>
          </motion.div>
          <div className="flex flex-col">
            <span className="font-semibold tracking-tight text-zinc-100">FinLLM</span>
            <span className="font-mono text-[9px] tracking-[0.2em] text-zinc-500 -mt-0.5">
              ÇİFT PAZAR
            </span>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-8 text-sm">
          <Link href="/features" className="text-zinc-400 hover:text-zinc-100 transition">
            Özellikler
          </Link>
          <Link href="/about" className="text-zinc-400 hover:text-zinc-100 transition">
            Hakkımızda
          </Link>
          <Link
            href="/app/signals"
            className="text-zinc-400 hover:text-zinc-100 transition flex items-center gap-1.5"
          >
            Canlı Sinyaller
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          </Link>
        </nav>

        <Link
          href="/app/signals"
          className="hidden md:inline-flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-violet-500 hover:from-cyan-400 hover:to-violet-400 text-white px-4 py-1.5 rounded-md text-sm font-medium transition shadow-lg shadow-cyan-500/20"
        >
          Panele Git
          <span aria-hidden>→</span>
        </Link>
      </div>
    </motion.header>
  );
}
