"use client";

import { motion } from "framer-motion";

export function LiveExample() {
  return (
    <section className="relative py-32 px-6 border-t border-zinc-900 overflow-hidden">
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-emerald-500/10 rounded-full blur-[100px]" />
      </div>

      <div className="mx-auto max-w-7xl">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="mb-12"
        >
          <div className="font-mono text-[11px] tracking-[0.3em] text-emerald-300/80">
            CANLI ÖRNEK
          </div>
          <h2 className="mt-3 text-4xl md:text-5xl font-bold tracking-tight text-zinc-100 max-w-2xl">
            Üretimde dönen bir analist çıktısı
          </h2>
          <p className="mt-5 text-zinc-400 max-w-2xl text-lg leading-relaxed">
            Hiçbir sayı uydurulmaz; her metrik veri bloğundan üretilir.
            Yapay zekanın araç çağrısı (tool calling) ile zorlanmış kaynak
            bütünlüğü, halüsinasyona karşı tasarım düzeyinde koruma sağlar.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="rounded-2xl border border-zinc-800 bg-zinc-950/60 backdrop-blur overflow-hidden shadow-2xl shadow-emerald-500/5"
        >
          <div className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <span className="px-3 py-1 rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-sm font-semibold">
                GÜÇLÜ AL
              </span>
              <span className="text-2xl font-bold text-zinc-100">GOOGL</span>
              <span className="text-zinc-500 text-sm">
                Alphabet · İletişim Hizmetleri
              </span>
            </div>
            <div className="flex items-center gap-4 text-sm">
              <div className="text-right">
                <div className="font-mono text-[10px] text-zinc-500">KALİBRE GÜVEN</div>
                <div className="text-zinc-100 font-bold tabular-nums">0.62</div>
              </div>
              <div className="w-px h-8 bg-zinc-800" />
              <div className="text-right">
                <div className="font-mono text-[10px] text-zinc-500">BEKLENEN GETİRİ</div>
                <div className="text-emerald-300 font-bold tabular-nums">+7,8%</div>
              </div>
              <div className="w-px h-8 bg-zinc-800" />
              <div className="text-right">
                <div className="font-mono text-[10px] text-zinc-500">VADE</div>
                <div className="text-zinc-100 font-bold tabular-nums">20 gün</div>
              </div>
            </div>
          </div>

          <div className="grid lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-zinc-800">
            <div className="p-6 space-y-4 text-sm">
              <div>
                <div className="font-mono text-[10px] text-cyan-300/80 tracking-[0.2em] mb-2">
                  TREND ANALİZİ
                </div>
                <p className="text-zinc-300 leading-relaxed">
                  Hareketli ortalamalar altın kesişimde; 20, 50 ve 200 günlükler
                  güçlü bir hiyerarşi içinde yükseliyor. ADX 48,96 değeriyle
                  güçlü trend rejimini; DI yönü ise alıcı baskısını teyit ediyor.
                </p>
              </div>

              <div>
                <div className="font-mono text-[10px] text-violet-300/80 tracking-[0.2em] mb-2">
                  FORMASYON
                </div>
                <p className="text-zinc-300 leading-relaxed">
                  EMA21'e geri çekiliş tamamlanmış; fiyat 376,05'ten %2,09'luk
                  bir geri çekilişle test edilmiş, ardından hacim kurumasıyla
                  birlikte yeşil mum oluşmuş. Klasik bir devam kurulumu.
                </p>
              </div>

              <div>
                <div className="font-mono text-[10px] text-amber-300/80 tracking-[0.2em] mb-2">
                  TEMEL ANALİZ (KATMAN 7)
                </div>
                <p className="text-zinc-300 leading-relaxed">
                  Kaliteli temellerle destekleniyor: ROE %38,9 · Net Kâr Marjı
                  %37,9 · Yıllık Kâr Büyümesi +%82. F/K 24,5; sektör medyanı
                  olan 28'e göre makul fiyatlanmış.
                </p>
              </div>

              <div>
                <div className="font-mono text-[10px] text-rose-300/80 tracking-[0.2em] mb-2">
                  RİSKLER
                </div>
                <ul className="text-zinc-400 leading-relaxed space-y-1">
                  <li>• RSI14 = 70,30 — aşırı alım bölgesi</li>
                  <li>• Tepki hacmi normal (0,95×); kırılım teyidi zayıf</li>
                  <li>• OBV negatif uyumsuzluk — kurumsal uyarı</li>
                </ul>
              </div>
            </div>

            <div className="p-6 space-y-5 text-sm">
              <div>
                <div className="font-mono text-[10px] text-zinc-500 tracking-[0.2em] mb-3">
                  FİYAT SENARYOLARI
                </div>
                <div className="space-y-2">
                  {[
                    { label: "Temel", prob: 55, target: 422.0, ret: 8.2, color: "zinc" },
                    { label: "İyimser", prob: 25, target: 448.0, ret: 14.9, color: "emerald" },
                    { label: "Kötümser", prob: 20, target: 376.0, ret: -3.6, color: "rose" },
                  ].map((sc) => (
                    <div
                      key={sc.label}
                      className="flex items-center gap-3 p-2 rounded bg-zinc-900/50"
                    >
                      <div
                        className={`font-mono text-xs font-bold w-20 ${
                          sc.color === "emerald"
                            ? "text-emerald-400"
                            : sc.color === "rose"
                              ? "text-rose-400"
                              : "text-zinc-400"
                        }`}
                      >
                        {sc.label}
                      </div>
                      <div className="flex-1">
                        <div className="h-1.5 bg-zinc-800 rounded overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            whileInView={{ width: `${sc.prob}%` }}
                            viewport={{ once: true }}
                            transition={{ duration: 1, delay: 0.3 }}
                            className={`h-full ${
                              sc.color === "emerald"
                                ? "bg-emerald-500"
                                : sc.color === "rose"
                                  ? "bg-rose-500"
                                  : "bg-zinc-500"
                            }`}
                          />
                        </div>
                        <div className="mt-0.5 text-[10px] font-mono text-zinc-500">
                          %{sc.prob} olasılık
                        </div>
                      </div>
                      <div className="font-mono text-zinc-100 tabular-nums w-16 text-right">
                        ${sc.target.toFixed(0)}
                      </div>
                      <div
                        className={`font-mono tabular-nums text-xs w-16 text-right ${
                          sc.ret >= 0 ? "text-emerald-400" : "text-rose-400"
                        }`}
                      >
                        {sc.ret >= 0 ? "+" : ""}
                        {sc.ret.toFixed(1)}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <div className="font-mono text-[10px] text-zinc-500 tracking-[0.2em] mb-3">
                  TAHSİS (KELLY ORANI)
                </div>
                <div className="rounded bg-emerald-500/10 border border-emerald-500/30 p-3">
                  <div className="flex items-baseline justify-between mb-2">
                    <span className="text-zinc-300">Pozisyon büyüklüğü</span>
                    <span className="font-mono text-emerald-300 tabular-nums text-lg font-bold">
                      2.500 $
                    </span>
                  </div>
                  <div className="h-1.5 bg-zinc-900 rounded overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      whileInView={{ width: "25%" }}
                      viewport={{ once: true }}
                      transition={{ duration: 1.2, delay: 0.5 }}
                      className="h-full bg-emerald-400"
                    />
                  </div>
                  <div className="mt-2 flex justify-between text-[11px] font-mono text-zinc-500">
                    <span>Portföyün %25'i</span>
                    <span>%15 nakit tampon</span>
                  </div>
                </div>
              </div>

              <div>
                <div className="font-mono text-[10px] text-zinc-500 tracking-[0.2em] mb-3">
                  UYARI BAYRAKLARI
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {[
                    "RSI_AŞIRI_ALIM",
                    "OBV_NEGATİF_UYUMSUZLUK",
                    "SALINIM_TEPESİNE_YAKIN",
                    "PAHALI_ÇARPAN",
                  ].map((flag) => (
                    <span
                      key={flag}
                      className="text-[10px] font-mono px-2 py-0.5 rounded border border-amber-800/40 bg-amber-900/30 text-amber-300/80"
                    >
                      {flag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="border-t border-zinc-800 px-6 py-3 flex items-center justify-between text-[11px] font-mono text-zinc-500">
            <span>claude-opus-4-7 · tur nasdaq-ön_seans-21734653</span>
            <span>maliyet 0,204 $ · süre 6,8 sn</span>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
