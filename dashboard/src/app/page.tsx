import type { Metadata } from "next";

import { CTA } from "@/marketing/CTA";
import { Hero } from "@/marketing/Hero";
import { LayerDecision } from "@/marketing/LayerDecision";
import { LiveExample } from "@/marketing/LiveExample";
import { MarketingFooter } from "@/marketing/Footer";
import { MarketingNavbar } from "@/marketing/Navbar";
import { Pillars } from "@/marketing/Pillars";
import { Pipeline } from "@/marketing/Pipeline";
import { Problem } from "@/marketing/Problem";
import { SmoothScrollProvider } from "@/marketing/SmoothScrollProvider";
import { Stats } from "@/marketing/Stats";

export const metadata: Metadata = {
  title: "FinLLM — Yapay Zeka Destekli Orta Vadeli Sermaye Piyasası Sinyalleri",
  description:
    "BIST ve NASDAQ için yedi katmanlı karar mimarisi, kalibre edilmiş güven ve geriye dönük test kapısı ile çalışan kurumsal düzey orta vadeli sinyal sistemi.",
  openGraph: {
    title: "FinLLM — Orta Vadeli Yatırım Sinyalleri",
    description: "Çift pazar yapay zeka platformu · BIST + NASDAQ · gerçek zamanlı panel",
    type: "website",
  },
};

export default function HomePage() {
  return (
    <SmoothScrollProvider>
      <main className="relative min-h-screen bg-black text-zinc-100 overflow-x-hidden">
        <MarketingNavbar />
        <Hero />
        <Problem />
        <Pillars />
        <Pipeline />
        <LayerDecision />
        <LiveExample />
        <Stats />
        <CTA />
        <MarketingFooter />
      </main>
    </SmoothScrollProvider>
  );
}
