import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    template: "%s · FinLLM",
    default: "FinLLM — Yapay Zeka Destekli Orta Vadeli Sermaye Piyasası Sinyalleri",
  },
  description:
    "FinLLM, BIST ve NASDAQ için yedi katmanlı karar mimarisiyle çalışan, kalibre edilmiş güven skoruna sahip kurumsal düzeyde orta vadeli sinyal sistemidir.",
  keywords: [
    "orta vadeli sinyal",
    "borsa sinyali",
    "yapay zeka borsa",
    "BIST sinyal",
    "NASDAQ sinyal",
    "yatırım panosu",
    "teknik analiz",
    "temel analiz",
    "kantitatif analiz",
    "FinLLM",
  ],
  authors: [{ name: "Muzaffer Berke Savaş" }],
  openGraph: {
    title: "FinLLM — Orta Vadeli Yatırım Sinyalleri",
    description:
      "Yapay zeka destekli, kalibre edilmiş, kurumsal düzeyde orta vadeli pozisyon sinyalleri. BIST ve NASDAQ tek panelde.",
    type: "website",
    locale: "tr_TR",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="tr"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body className="min-h-full bg-black text-zinc-100 selection:bg-cyan-500/30 selection:text-white">
        {children}
      </body>
    </html>
  );
}
