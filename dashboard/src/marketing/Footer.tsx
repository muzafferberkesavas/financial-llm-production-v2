import Link from "next/link";

export function MarketingFooter() {
  return (
    <footer className="border-t border-zinc-900 py-12 px-6">
      <div className="mx-auto max-w-7xl">
        <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-8">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="relative w-7 h-7">
                <div className="absolute inset-0 bg-gradient-to-br from-cyan-400 to-violet-500 rounded" />
                <div className="absolute inset-[2px] bg-black rounded-[2px] flex items-center justify-center font-mono text-xs font-bold">
                  ƒ
                </div>
              </div>
              <span className="font-semibold text-zinc-100">FinLLM</span>
            </div>
            <p className="text-xs text-zinc-500 leading-relaxed">
              Yapay zeka destekli, kalibre edilmiş, kurumsal düzeyde orta vadeli
              sermaye piyasası sinyalleri.
            </p>
            <p className="mt-3 text-xs text-zinc-600">
              BIST · NASDAQ · Çift pazar tek panel.
            </p>
          </div>

          <div>
            <div className="font-mono text-[10px] tracking-[0.3em] text-zinc-500 mb-3">
              ÜRÜN
            </div>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/features" className="text-zinc-400 hover:text-zinc-100 transition">
                  Özellikler
                </Link>
              </li>
              <li>
                <Link href="/app/signals" className="text-zinc-400 hover:text-zinc-100 transition">
                  Canlı Sinyaller
                </Link>
              </li>
              <li>
                <Link href="/app/portfolio" className="text-zinc-400 hover:text-zinc-100 transition">
                  Portföy
                </Link>
              </li>
              <li>
                <Link href="/app/history" className="text-zinc-400 hover:text-zinc-100 transition">
                  Geçmiş Performans
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <div className="font-mono text-[10px] tracking-[0.3em] text-zinc-500 mb-3">
              KURUMSAL
            </div>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/about" className="text-zinc-400 hover:text-zinc-100 transition">
                  Hakkımızda
                </Link>
              </li>
              <li>
                <a
                  href="https://github.com/muzafferberkesavas/financial-llm-production"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-zinc-400 hover:text-zinc-100 transition"
                >
                  GitHub
                </a>
              </li>
              <li>
                <a
                  href="mailto:savasmuzafferberke@gmail.com"
                  className="text-zinc-400 hover:text-zinc-100 transition"
                >
                  İletişim
                </a>
              </li>
            </ul>
          </div>

          <div>
            <div className="font-mono text-[10px] tracking-[0.3em] text-zinc-500 mb-3">
              YASAL UYARI
            </div>
            <p className="text-xs text-zinc-500 leading-relaxed">
              Bu platform yatırım danışmanlığı kapsamında değildir; yer alan
              sinyaller bilgilendirme ve araştırma amaçlıdır. Her yatırımcının
              kendi araştırmasını yapması ve risk profiline uygun kararlar
              vermesi esastır.
            </p>
          </div>
        </div>

        <div className="mt-12 pt-6 border-t border-zinc-900 flex items-center justify-between text-xs text-zinc-500 font-mono">
          <span>© 2026 FinLLM</span>
          <span>finllm.ai</span>
        </div>
      </div>
    </footer>
  );
}
