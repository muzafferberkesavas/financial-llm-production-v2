import type { Metadata } from "next";
import Link from "next/link";

import { MarketingFooter } from "@/marketing/Footer";
import { MarketingNavbar } from "@/marketing/Navbar";

export const metadata: Metadata = {
  title: "Özellikler",
  description:
    "FinLLM'in çift pazar mimarisi, yapay zeka karar katmanları, temel-teknik birleşimi ve kalibrasyon altyapısı.",
};

const FEATURES = [
  {
    title: "Çift Pazar Mimarisi",
    body: "Tek bir arka uç hem BIST hem de NASDAQ'ı eşzamanlı işler. Piyasaya özgü eşikler, takas kuralları (T+1 ve T+2) ve maliyet yapıları (BSMV, komisyon, kayma) otomatik olarak uygulanır.",
    code: "PAZAR",
    bullet: [
      "BIST: .IS son eki, TL fiyatlandırma, ons/gram emtia dönüşümü",
      "NASDAQ: S&P 500 ve Russell 1000 genişliği, doğrudan sembol biçimi",
      "Yeni bir borsayı sisteme eklemek yaklaşık elli satır kod ile mümkün",
    ],
  },
  {
    title: "Claude Opus 4.7 ve Haiku 4.5",
    body: "İki aşamalı yapay zeka mimarisi: ucuz tarayıcı (Haiku) ve derin analist (Opus). Yapılandırılmış araç çağrısı ile şema-doğrulamalı JSON; önek-önbellek ile %90'a varan maliyet tasarrufu.",
    code: "YAPAY ZEKA",
    bullet: [
      "Derin analist sistem yönergesi: yedi katmanlı analiz ve sekiz bileşenli bileşke",
      "Her sayı için kaynak zorunluluğu; kaynaksız ifadeler otomatik düşürülür",
      "Yeniden deneme, başarısızlık tolerans katmanı ve kullanım başına maliyet izlemesi",
    ],
  },
  {
    title: "Temel ve Teknik Analiz Birleşimi",
    body: "F/K, ROE, kâr marjları ve büyüme oranları ile birlikte otuzun üzerinde teknik gösterge. Sektör medyanı karşılaştırması; bilanço yaklaşan hisseler için otomatik uyarı.",
    code: "ANALİZ",
    bullet: [
      "Yirmi temel veri alanı (Yahoo Finance kapsamlı veri seti üzerinden)",
      "Değer (40) + Kalite (30) + Büyüme (30) = yüz puanlık temel skor",
      "Sektör medyanına göre F/K, F/B, FAVÖK çarpanı karşılaştırması",
      "RSI, MACD, Bollinger, ADX, OBV, Ichimoku, Supertrend, Fibonacci dahil 30+ gösterge",
    ],
  },
  {
    title: "Haber Katmanı (Sıfırıncı Katman)",
    body: "RSS, SEC EDGAR (8-K, 10-Q), Finnhub ve KAP haber akışları Claude Haiku tarafından yapılandırılmış on başlıklı İngilizce gündeme dönüştürülür.",
    code: "HABER",
    bullet: [
      "Anthropic üç katmanlı güvensiz girdi izolasyon örüntüsü",
      "Ham haber asla derin analiste iletilmez; yalnızca süzülmüş özet",
      "Duygu skoru, sembol ve tarih etiketli yapılandırılmış biçim",
    ],
  },
  {
    title: "Olasılık Kalibrasyonu",
    body: "Yapay zekanın güven skoru, gerçek isabet oranına eşit değildir. Platt ölçeklemesi ile geçmiş sonuçlardan kalibrasyon yapılır; pozisyon büyüklüğü Kelly kriteri ile belirlenir.",
    code: "KALİBRASYON",
    bullet: [
      "Sonuç takibi: her sinyalin yaşam döngüsü veri tabanında tutulur",
      "Otuzdan fazla kapanmış sonuçtan sonra Platt modeli otomatik eğitilir",
      "Kelly tahsisi: f* = (p · b − q) / b formülü ile pozisyon büyüklüğü",
    ],
  },
  {
    title: "Geriye Dönük Test Kapısı ve Güvenlik Mekanizmaları",
    body: "VIX güvenlik kesicisi, çoklu teyit kuralı, son otuz günlük kağıt-üzeri test ve rejime duyarlı pozisyon büyüklüğü. Hatalı sinyaller otomatik olarak düşürülür.",
    code: "RİSK YÖNETİMİ",
    bullet: [
      "VIX 35'in üzerindeyse işlem askıya alınır",
      "En az üç teyit aranır; aksi halde sinyal kategorisi düşer",
      "Gerçekçi işlem maliyetleri: BIST komisyon ve BSMV, NASDAQ slipaj",
      "Otuz günlük kağıt-üzeri testte isabet oranı %40'ın altında ise başarısız sayılır",
    ],
  },
  {
    title: "Üç Stratejili Topluluk",
    body: "EMA'ya geri çekiliş, bilanço sonrası seyir ve sektör rotasyonu. Piyasa rejimine göre aktif strateji seçimi.",
    code: "STRATEJİ",
    bullet: [
      "Geri çekiliş: klasik trend devam örüntüsü",
      "Bilanço sonrası seyir: akademik literatürün en güçlü anomalisi (Foster, 1984)",
      "Sektör rotasyonu: momentum + göreli güç + hacim eğilimi",
    ],
  },
  {
    title: "Üç Kanal Dağıtım",
    body: "Telegram (kanal yayını ve özel mesaj), web paneli (Next.js) ve mobil uygulama (Flutter). Tek bir arka uç; üç ayrı dağıtım kanalı.",
    code: "KANALLAR",
    bullet: [
      "Telegram: /sinyal AAPL · /portfoy · /takip-listesi komutları",
      "Web paneli: canlı sinyaller, portföy, geçmiş performans",
      "Mobil: yerel önbellek ve mobil bildirim altyapısı",
    ],
  },
];

export default function FeaturesPage() {
  return (
    <main className="relative min-h-screen bg-black text-zinc-100">
      <MarketingNavbar />

      <section className="pt-32 pb-16 px-6">
        <div className="mx-auto max-w-7xl">
          <div className="font-mono text-[11px] tracking-[0.3em] text-cyan-300/80">
            ÖZELLİKLER
          </div>
          <h1 className="mt-3 text-5xl md:text-6xl font-bold tracking-tight">
            <span className="text-zinc-100">Üretim seviyesi.</span>
            <br />
            <span className="bg-gradient-to-br from-cyan-300 to-violet-400 bg-clip-text text-transparent">
              Sekiz modülün tamamı canlı.
            </span>
          </h1>
          <p className="mt-6 text-lg text-zinc-400 max-w-2xl">
            Anthropic finansal hizmetler örüntüleri, kantitatif akademik
            altyapı ve modern veri mühendisliği aynı süreçte bütünleşir.
          </p>
        </div>
      </section>

      <section className="pb-32 px-6">
        <div className="mx-auto max-w-7xl space-y-4">
          {FEATURES.map((f, i) => (
            <div
              key={f.code}
              className="grid md:grid-cols-3 gap-8 rounded-2xl border border-zinc-800 bg-zinc-950/40 backdrop-blur p-8"
            >
              <div className="md:col-span-1">
                <div className="font-mono text-[10px] tracking-[0.3em] text-cyan-300/80">
                  {f.code} · {String(i + 1).padStart(2, "0")}
                </div>
                <h2 className="mt-2 text-2xl font-bold text-zinc-100">
                  {f.title}
                </h2>
              </div>
              <div className="md:col-span-2 space-y-4">
                <p className="text-zinc-300 leading-relaxed">{f.body}</p>
                <ul className="space-y-2">
                  {f.bullet.map((b) => (
                    <li
                      key={b}
                      className="flex items-start gap-3 text-sm text-zinc-400"
                    >
                      <span className="mt-1.5 w-1 h-1 rounded-full bg-cyan-400 flex-shrink-0" />
                      <span>{b}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-16 text-center">
          <Link
            href="/app/signals"
            className="inline-flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-violet-500 hover:from-cyan-400 hover:to-violet-400 text-white px-8 py-4 rounded-md font-medium shadow-2xl shadow-cyan-500/30 transition"
          >
            Canlı Paneli Görüntüle →
          </Link>
        </div>
      </section>

      <MarketingFooter />
    </main>
  );
}
