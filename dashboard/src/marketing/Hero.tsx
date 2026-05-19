"use client";

import Link from "next/link";
import {
  motion,
  useMotionTemplate,
  useMotionValue,
  useSpring,
  useTransform,
} from "framer-motion";
import { useEffect, useRef, useState } from "react";

export function Hero() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [mounted, setMounted] = useState(false);

  // Mouse-tracking parallax
  const mouseX = useMotionValue(0.5);
  const mouseY = useMotionValue(0.5);
  const springX = useSpring(mouseX, { stiffness: 50, damping: 20 });
  const springY = useSpring(mouseY, { stiffness: 50, damping: 20 });
  const orbCyanX = useTransform(springX, [0, 1], [-40, 40]);
  const orbCyanY = useTransform(springY, [0, 1], [-30, 30]);
  const orbVioletX = useTransform(springX, [0, 1], [40, -40]);
  const orbVioletY = useTransform(springY, [0, 1], [30, -30]);
  const spotlightX = useTransform(springX, [0, 1], [0, 100]);
  const spotlightY = useTransform(springY, [0, 1], [0, 100]);
  const spotlightBg = useMotionTemplate`radial-gradient(circle at ${spotlightX}% ${spotlightY}%, rgba(34,211,238,0.08), transparent 45%)`;

  // 3D card tilt
  const cardTiltX = useTransform(springY, [0, 1], [6, -6]);
  const cardTiltY = useTransform(springX, [0, 1], [-6, 6]);

  useEffect(() => {
    const handleMouse = (e: MouseEvent) => {
      mouseX.set(e.clientX / window.innerWidth);
      mouseY.set(e.clientY / window.innerHeight);
    };
    window.addEventListener("mousemove", handleMouse);
    return () => window.removeEventListener("mousemove", handleMouse);
  }, [mouseX, mouseY]);

  useEffect(() => {
    setMounted(true);
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrame: number;
    let t = 0;
    const dpr = window.devicePixelRatio || 1;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    };
    resize();
    window.addEventListener("resize", resize);

    const draw = () => {
      t += 0.012;
      const w = canvas.width / dpr;
      const h = canvas.height / dpr;
      ctx.clearRect(0, 0, w, h);

      // Grid
      ctx.strokeStyle = "rgba(63, 63, 70, 0.3)";
      ctx.lineWidth = 1;
      for (let i = 0; i < 10; i++) {
        ctx.beginPath();
        ctx.moveTo(0, (h / 10) * i);
        ctx.lineTo(w, (h / 10) * i);
        ctx.stroke();
      }

      // Sinyal hattı
      const points: { x: number; y: number }[] = [];
      for (let x = 0; x <= w; x += 4) {
        const phase = (x / w) * Math.PI * 4 + t;
        const y =
          h * 0.5 +
          Math.sin(phase) * h * 0.15 +
          Math.sin(phase * 2.3 + t * 0.7) * h * 0.08 +
          Math.cos(phase * 0.7 + t * 1.4) * h * 0.05;
        points.push({ x, y });
      }

      const gradient = ctx.createLinearGradient(0, 0, 0, h);
      gradient.addColorStop(0, "rgba(34, 211, 238, 0.25)");
      gradient.addColorStop(1, "rgba(168, 85, 247, 0)");

      ctx.beginPath();
      ctx.moveTo(0, h);
      points.forEach((p) => ctx.lineTo(p.x, p.y));
      ctx.lineTo(w, h);
      ctx.closePath();
      ctx.fillStyle = gradient;
      ctx.fill();

      ctx.beginPath();
      points.forEach((p, i) => {
        if (i === 0) ctx.moveTo(p.x, p.y);
        else ctx.lineTo(p.x, p.y);
      });
      ctx.strokeStyle = "rgba(34, 211, 238, 0.9)";
      ctx.lineWidth = 2;
      ctx.lineCap = "round";
      ctx.shadowColor = "rgba(34, 211, 238, 0.6)";
      ctx.shadowBlur = 20;
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Sinyal noktaları
      const markers = [0.2, 0.45, 0.68, 0.85];
      markers.forEach((m) => {
        const i = Math.floor(points.length * m);
        if (!points[i]) return;
        const isBuy = m === 0.2 || m === 0.68;
        ctx.beginPath();
        ctx.arc(points[i].x, points[i].y, 5, 0, Math.PI * 2);
        ctx.fillStyle = isBuy ? "rgba(52, 211, 153, 1)" : "rgba(244, 114, 182, 1)";
        ctx.fill();
        ctx.beginPath();
        ctx.arc(points[i].x, points[i].y, 12, 0, Math.PI * 2);
        ctx.strokeStyle = isBuy
          ? "rgba(52, 211, 153, 0.4)"
          : "rgba(244, 114, 182, 0.4)";
        ctx.lineWidth = 1;
        ctx.stroke();
      });

      animationFrame = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(animationFrame);
    };
  }, []);

  return (
    <section className="relative min-h-screen flex items-center overflow-hidden">
      <div className="absolute inset-0 -z-10">
        <motion.div
          style={{ x: orbCyanX, y: orbCyanY }}
          className="absolute top-1/4 left-1/4 w-[600px] h-[600px] bg-cyan-500/20 rounded-full blur-[120px]"
        />
        <motion.div
          style={{ x: orbVioletX, y: orbVioletY }}
          className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-violet-500/20 rounded-full blur-[120px]"
        />
        <motion.div
          className="absolute inset-0 opacity-50"
          style={{ background: spotlightBg }}
        />
        <div
          className="absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(circle at 1px 1px, rgba(255,255,255,0.06) 1px, transparent 0)",
            backgroundSize: "32px 32px",
          }}
        />
      </div>

      <div className="relative mx-auto max-w-7xl px-6 grid md:grid-cols-2 gap-12 items-center pt-28 pb-20">
        {/* Left — text */}
        <div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900/50 backdrop-blur px-3 py-1 text-xs font-mono"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-zinc-400">FAZ 3 CANLI</span>
            <span className="text-zinc-600">·</span>
            <span className="text-zinc-400">BIST + NASDAQ</span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="mt-6 text-5xl md:text-6xl font-bold tracking-tight leading-[1.05]"
          >
            <span className="text-zinc-100">Yapay zeka destekli</span>
            <br />
            <span className="bg-gradient-to-br from-cyan-300 via-cyan-400 to-violet-400 bg-clip-text text-transparent">
              orta vadeli sinyaller.
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="mt-6 text-lg text-zinc-400 max-w-lg leading-relaxed"
          >
            Claude Opus 4.7 ile analist düzeyinde teknik ve temel analiz.
            BIST ve NASDAQ'ta yedi katmanlı karar mantığı, kalibre edilmiş
            güven skorları ve geriye dönük test kapısı.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-10 flex flex-wrap gap-4"
          >
            <Link
              href="/app/signals"
              className="group inline-flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-violet-500 hover:from-cyan-400 hover:to-violet-400 text-white px-6 py-3 rounded-md font-medium shadow-2xl shadow-cyan-500/30 transition"
            >
              Canlı Sinyalleri Gör
              <span className="transition group-hover:translate-x-1">→</span>
            </Link>
            <Link
              href="/features"
              className="inline-flex items-center gap-2 border border-zinc-700 hover:border-zinc-500 text-zinc-300 hover:text-white px-6 py-3 rounded-md font-medium transition"
            >
              Sistem Nasıl Çalışır?
            </Link>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="mt-12 flex items-center gap-8 font-mono text-xs text-zinc-500"
          >
            <div>
              <div className="text-2xl text-zinc-100 font-bold tabular-nums">
                ~25<span className="text-zinc-500">sn</span>
              </div>
              <div className="mt-1">Tek tur süresi</div>
            </div>
            <div className="w-px h-12 bg-zinc-800" />
            <div>
              <div className="text-2xl text-zinc-100 font-bold tabular-nums">
                7
              </div>
              <div className="mt-1">Karar katmanı</div>
            </div>
            <div className="w-px h-12 bg-zinc-800" />
            <div>
              <div className="text-2xl text-zinc-100 font-bold tabular-nums">
                30<span className="text-zinc-500">+</span>
              </div>
              <div className="mt-1">Teknik gösterge</div>
            </div>
          </motion.div>
        </div>

        {/* Right — 3D-tilted chart card */}
        <motion.div
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, delay: 0.3 }}
          className="relative"
          style={{ perspective: 1200 }}
        >
          <motion.div
            style={{ rotateX: cardTiltX, rotateY: cardTiltY, transformStyle: "preserve-3d" }}
            className="relative aspect-[4/3] rounded-xl border border-zinc-800 bg-zinc-950/40 backdrop-blur overflow-hidden"
          >
            <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-4 py-3 border-b border-zinc-800 bg-zinc-950/80">
              <div className="flex items-center gap-2">
                <div className="flex gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-rose-500/60" />
                  <div className="w-2.5 h-2.5 rounded-full bg-amber-500/60" />
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/60" />
                </div>
                <div className="ml-4 font-mono text-xs text-zinc-500">
                  finllm.ai/app/sinyaller
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  GÜÇLÜ AL
                </span>
                <span className="font-mono text-xs text-zinc-100 tabular-nums">
                  NVDA
                </span>
              </div>
            </div>

            <canvas
              ref={canvasRef}
              className="absolute inset-0 w-full h-full mt-12"
            />

            {mounted && (
              <>
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: 0.8 }}
                  className="absolute bottom-4 left-4 right-1/2 mr-2 rounded-lg border border-zinc-800 bg-zinc-950/90 backdrop-blur px-3 py-2 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-zinc-500">KALİBRE GÜVEN</span>
                    <span className="font-mono text-emerald-300 tabular-nums">
                      0.78
                    </span>
                  </div>
                  <div className="mt-1 h-1 bg-zinc-800 rounded overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: "78%" }}
                      transition={{ duration: 1.2, delay: 1 }}
                      className="h-full bg-gradient-to-r from-cyan-400 to-emerald-400"
                    />
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: 1.0 }}
                  className="absolute bottom-4 right-4 left-1/2 ml-2 rounded-lg border border-zinc-800 bg-zinc-950/90 backdrop-blur px-3 py-2 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-zinc-500">BEKLENEN GETİRİ</span>
                    <span className="font-mono text-cyan-300 tabular-nums">
                      +14.2%
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-1 text-[10px] font-mono text-zinc-500">
                    <span>18 gün vade</span>
                    <span className="text-zinc-700">·</span>
                    <span>GÜÇLÜ TREND</span>
                  </div>
                </motion.div>
              </>
            )}
          </motion.div>

          {/* Floating tickers */}
          <motion.div
            animate={{ y: [0, -8, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
            className="absolute -top-4 -right-2 px-3 py-1.5 rounded-md bg-zinc-950 border border-cyan-500/30 text-xs font-mono shadow-xl"
          >
            <div className="text-cyan-400">THYAO.IS</div>
            <div className="text-emerald-400 tabular-nums">+8.4%</div>
          </motion.div>
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut", delay: 1 }}
            className="absolute -bottom-4 -left-4 px-3 py-1.5 rounded-md bg-zinc-950 border border-violet-500/30 text-xs font-mono shadow-xl"
          >
            <div className="text-violet-400">AAPL</div>
            <div className="text-emerald-400 tabular-nums">+11.7%</div>
          </motion.div>
          <motion.div
            animate={{ y: [0, -6, 0], x: [0, 4, 0] }}
            transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: 0.6 }}
            className="hidden md:block absolute top-1/2 -left-8 px-3 py-1.5 rounded-md bg-zinc-950 border border-amber-500/30 text-xs font-mono shadow-xl"
          >
            <div className="text-amber-400">EREGL.IS</div>
            <div className="text-rose-400 tabular-nums">-2.1%</div>
          </motion.div>
        </motion.div>
      </div>

      {/* Bottom marquee */}
      <div className="absolute bottom-0 left-0 right-0 border-t border-zinc-900 bg-black/40 backdrop-blur py-3 overflow-hidden">
        <div className="flex gap-12 font-mono text-[11px] tracking-[0.2em] text-zinc-600 whitespace-nowrap">
          <motion.div
            animate={{ x: [0, -1200] }}
            transition={{ duration: 35, repeat: Infinity, ease: "linear" }}
            className="flex gap-12 flex-shrink-0"
          >
            {[
              "ANTHROPIC CLAUDE OPUS 4.7",
              "BIST 100 + NASDAQ",
              "PLATT KALİBRASYONU",
              "KELLY KRİTERİ",
              "FINNHUB · SEC EDGAR · YAHOO FINANCE",
              "30+ TEKNİK GÖSTERGE",
              "TEMEL ANALİZ KATMANI",
              "GERİYE DÖNÜK TEST KAPISI",
              "ANTHROPIC CLAUDE OPUS 4.7",
              "BIST 100 + NASDAQ",
              "PLATT KALİBRASYONU",
              "KELLY KRİTERİ",
            ].map((label, i) => (
              <span key={i} className="flex items-center gap-12">
                {label}
                <span className="text-zinc-700">◆</span>
              </span>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  );
}
