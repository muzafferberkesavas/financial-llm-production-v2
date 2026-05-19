import type { Metadata } from "next";

import { MarketingFooter } from "@/marketing/Footer";
import { MarketingNavbar } from "@/marketing/Navbar";

export const metadata: Metadata = {
  title: "Hakkımızda",
  description: "FinLLM'in yaklaşımı, etiği ve şeffaflık ilkeleri.",
};

export default function AboutPage() {
  return (
    <main className="relative min-h-screen bg-black text-zinc-100">
      <MarketingNavbar />

      <section className="pt-32 pb-16 px-6">
        <div className="mx-auto max-w-3xl">
          <div className="font-mono text-[11px] tracking-[0.3em] text-cyan-300/80">
            HAKKIMIZDA
          </div>
          <h1 className="mt-3 text-5xl md:text-6xl font-bold tracking-tight">
            <span className="text-zinc-100">Manifesto.</span>
          </h1>
          <p className="mt-8 text-xl text-zinc-300 leading-relaxed">
            Sermaye piyasasında üstünlük; sihirli bir formülden değil,{" "}
            <em className="text-zinc-100 not-italic">
              doğru veri, kalibre edilmiş güven, disipline edilmiş risk ve
              sürekli geri-bildirim
            </em>{" "}
            gibi sıkıcı şeylerden gelir.
          </p>

          <div className="mt-12 space-y-8 text-zinc-400 leading-relaxed">
            <p>
              FinLLM, üç farklı disiplini tek bir süreçte birleştirir:
            </p>

            <ul className="space-y-3 ml-6">
              <li className="relative">
                <span className="absolute -left-6 top-2 w-2 h-2 rounded-full bg-cyan-400" />
                <strong className="text-zinc-100">Kantitatif analiz.</strong>{" "}
                Beş yüz hisseyi körlemesine yapay zekaya atmak yerine; klasik
                tarayıcı eşikleriyle ön eleme, EMA geri çekilişi, bilanço
                sonrası seyir ve sektör rotasyonu strateji topluluğu ile uygun
                kurulumların avlanması.
              </li>
              <li className="relative">
                <span className="absolute -left-6 top-2 w-2 h-2 rounded-full bg-violet-400" />
                <strong className="text-zinc-100">
                  Analist düzeyinde yapay zeka.
                </strong>{" "}
                Claude Opus 4.7 ile yedi katmanlı karar mantığı. Her sayı
                kaynağına işaretli; halüsinasyon koruması araç çağrısı
                (tool calling) ile tasarım düzeyinde sağlanır.
              </li>
              <li className="relative">
                <span className="absolute -left-6 top-2 w-2 h-2 rounded-full bg-emerald-400" />
                <strong className="text-zinc-100">Risk yönetimi.</strong> Platt
                ölçeklemesi ile kalibrasyon, Kelly kriteri ile pozisyon
                büyüklüğü, otuz günlük geriye dönük test kapısı ve VIX
                güvenlik kesicisi. Sinyal, ancak tüm güvenlik kapılarını
                geçtikten sonra yayınlanır.
              </li>
            </ul>

            <h2 className="text-2xl font-bold text-zinc-100 mt-12">
              Neden bu yaklaşım?
            </h2>
            <p>
              Anthropic finansal hizmetler örüntüleri (üç katmanlı güvensiz
              girdi izolasyonu, her sayının kaynağa bağlanması, yetenek
              kitaplığı yaklaşımı), kanıtlanmış kantitatif pratikler (sekiz
              bileşenli bileşke skoru ve etiket tabanlı semantik yönerge)
              ve modern veri mühendisliği (Yahoo Finance, Pandas-TA,
              scikit-learn Platt ölçeklemesi) bir araya geldiğinde —
              gerçek hayatta çalışan bir sistem ortaya çıkar.
            </p>
            <p>
              Tek bir göstergeye ya da tek bir yönergeye güvenmiyoruz.
              Bileşke skoru, temel analiz, haber katmanı, çoklu zaman dilimi
              hizalaması, rejim filtresi ve kalibrasyon — hepsi birlikte
              dayanıklı bir karar üretir.
            </p>

            <h2 className="text-2xl font-bold text-zinc-100 mt-12">
              Etik ve sorumluluk
            </h2>
            <p>
              FinLLM{" "}
              <strong className="text-zinc-100">
                yatırım danışmanlığı kapsamında değildir
              </strong>
              . Sinyaller analist düzeyinde bir taslak niteliğindedir; her
              kullanıcı kendi araştırmasını yapar, kendi kararını verir.
              Yayınlanan her sinyal "her sayı kaynağına işaretli" ilkesine
              tâbidir ve uyarı bayrakları açıkça gösterilir.
            </p>
            <p>
              Bir sinyalde{" "}
              <code className="text-rose-300 bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/20 font-mono text-sm">
                KAYNAKSIZ
              </code>{" "}
              bayrağı varsa, güven skoru otomatik olarak %30 düşürülür.
              Kalibrasyon henüz eğitilmemişse Kelly tahsisi "ham güven"
              olarak işaretlenir.
            </p>

            <h2 className="text-2xl font-bold text-zinc-100 mt-12">
              Açıklık ve şeffaflık
            </h2>
            <p>
              Sistemin tüm karar mantığı belgelenmiştir: yedi katmanlı sistem
              yönergesi, sekiz bileşenli bileşke skoru formülü, sektör
              karşılaştırma değerleri, kalibrasyon yöntemi (Platt
              ölçeklemesi) ve geriye dönük test kapısı koşulları. Hiçbir kara
              kutu bırakılmamıştır.
            </p>

            <h2 className="text-2xl font-bold text-zinc-100 mt-12">İletişim</h2>
            <p>
              Soru, geri bildirim veya iş birliği için:{" "}
              <a
                href="mailto:savasmuzafferberke@gmail.com"
                className="text-cyan-400 hover:text-cyan-300 underline underline-offset-4"
              >
                savasmuzafferberke@gmail.com
              </a>
            </p>
          </div>
        </div>
      </section>

      <MarketingFooter />
    </main>
  );
}
