<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { StockDetailResponse, Market } from "@/types";
import { fetchStockDetail } from "@/lib/api";

const props = defineProps<{ ticker: string }>();
const route = useRoute();
const router = useRouter();

const data = ref<StockDetailResponse | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

const market = ((route.query.market as string) || "bist") as Market;

onMounted(async () => {
  try {
    data.value = await fetchStockDetail(props.ticker, market);
  } catch (e: any) {
    error.value = e.message ?? "Veri yuklenemedi";
  } finally {
    loading.value = false;
  }
});

function fmtNum(val: number | null | undefined, decimals = 2): string {
  if (val == null) return "—";
  return val.toLocaleString("tr-TR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function fmtPct(val: number | null | undefined): string {
  if (val == null) return "—";
  const pct = val * 100;
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}

function fmtBigNum(val: number | null | undefined): string {
  if (val == null) return "—";
  const abs = Math.abs(val);
  if (abs >= 1e9) return `${(val / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${(val / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${(val / 1e3).toFixed(1)}K`;
  return val.toFixed(0);
}

function pctClass(val: number | null | undefined): string {
  if (val == null) return "text-muted";
  return val >= 0 ? "text-bull" : "text-bear";
}

const indicatorGroups: Record<string, { label: string; keys: { key: string; label: string }[] }> = {
  trend: {
    label: "Trend",
    keys: [
      { key: "sma_20", label: "SMA 20" },
      { key: "sma_50", label: "SMA 50" },
      { key: "sma_200", label: "SMA 200" },
      { key: "price_vs_sma20", label: "Fiyat/SMA20" },
      { key: "price_vs_sma50", label: "Fiyat/SMA50" },
      { key: "adx_14", label: "ADX" },
      { key: "supertrend_dir", label: "SuperTrend" },
    ],
  },
  momentum: {
    label: "Momentum",
    keys: [
      { key: "rsi_14", label: "RSI 14" },
      { key: "macd", label: "MACD" },
      { key: "macd_signal", label: "MACD Sinyal" },
      { key: "macd_hist", label: "MACD Hist" },
      { key: "stoch_k", label: "Stoch %K" },
      { key: "stoch_d", label: "Stoch %D" },
      { key: "cci_20", label: "CCI 20" },
      { key: "roc_10", label: "ROC 10" },
    ],
  },
  volatility: {
    label: "Volatilite",
    keys: [
      { key: "atr_14", label: "ATR 14" },
      { key: "atr_pct", label: "ATR %" },
      { key: "bb_pct", label: "BB %" },
      { key: "bb_width", label: "BB Genislik" },
      { key: "vol_20d", label: "Vol 20g" },
    ],
  },
  volume: {
    label: "Hacim",
    keys: [
      { key: "vol_ratio", label: "Hacim Orani" },
      { key: "mfi_14", label: "MFI 14" },
      { key: "cmf_20", label: "CMF 20" },
    ],
  },
};
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-6 p-4 md:p-6">
    <!-- Header -->
    <div class="flex items-center gap-3">
      <button class="rounded-lg border border-border px-3 py-1.5 text-sm text-muted hover:bg-surface-2" @click="router.back()">
        &larr; Geri
      </button>
      <h1 class="num text-2xl font-bold tracking-tight">{{ ticker }}</h1>
      <span class="rounded-md bg-surface-2 px-2 py-0.5 text-xs font-medium uppercase text-muted">{{ market }}</span>
    </div>

    <!-- Price banner -->
    <div v-if="data?.technicals?.price" class="card flex items-baseline gap-4 p-4">
      <span class="num text-3xl font-semibold">{{ fmtNum(data.technicals.price.close) }}</span>
      <span class="num text-sm" :class="pctClass(data.technicals.price.change_1d_pct)">
        1g {{ fmtPct(data.technicals.price.change_1d_pct) }}
      </span>
      <span class="num text-sm" :class="pctClass(data.technicals.price.change_5d_pct)">
        5g {{ fmtPct(data.technicals.price.change_5d_pct) }}
      </span>
      <span class="num text-sm" :class="pctClass(data.technicals.price.change_20d_pct)">
        20g {{ fmtPct(data.technicals.price.change_20d_pct) }}
      </span>
      <span class="ml-auto text-xs text-faint">{{ data.technicals.as_of }}</span>
    </div>

    <!-- Loading / Error -->
    <div v-if="loading" class="py-12 text-center text-muted">Yukleniyor...</div>
    <div v-else-if="error" class="rounded-xl border border-bear/30 bg-bear/5 p-4 text-sm text-bear">{{ error }}</div>

    <template v-else-if="data">
      <!-- 1. Ceyreklik Finansallar -->
      <section class="card overflow-hidden">
        <h2 class="border-b border-border px-5 py-3 text-sm font-semibold uppercase tracking-wide text-muted">
          Ceyreklik Finansallar
        </h2>
        <div v-if="data.quarterly_financials?.quarters?.length" class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-border text-left text-xs text-faint">
                <th class="px-4 py-2">Metrik</th>
                <th v-for="q in data.quarterly_financials.quarters" :key="q.period" class="px-4 py-2 text-right num">
                  {{ q.period }}
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border/50">
              <tr>
                <td class="px-4 py-1.5 text-muted">Gelir</td>
                <td v-for="q in data.quarterly_financials.quarters" :key="q.period" class="px-4 py-1.5 text-right num">{{ fmtBigNum(q.revenue) }}</td>
              </tr>
              <tr>
                <td class="px-4 py-1.5 text-muted">Net Kar</td>
                <td v-for="q in data.quarterly_financials.quarters" :key="q.period" class="px-4 py-1.5 text-right num" :class="pctClass(q.net_income)">{{ fmtBigNum(q.net_income) }}</td>
              </tr>
              <tr>
                <td class="px-4 py-1.5 text-muted">Brut Marj</td>
                <td v-for="q in data.quarterly_financials.quarters" :key="q.period" class="px-4 py-1.5 text-right num">{{ fmtPct(q.gross_margin) }}</td>
              </tr>
              <tr>
                <td class="px-4 py-1.5 text-muted">Faaliyet Marji</td>
                <td v-for="q in data.quarterly_financials.quarters" :key="q.period" class="px-4 py-1.5 text-right num">{{ fmtPct(q.operating_margin) }}</td>
              </tr>
              <tr>
                <td class="px-4 py-1.5 text-muted">Net Marj</td>
                <td v-for="q in data.quarterly_financials.quarters" :key="q.period" class="px-4 py-1.5 text-right num">{{ fmtPct(q.net_margin) }}</td>
              </tr>
              <tr>
                <td class="px-4 py-1.5 text-muted">Toplam Borc</td>
                <td v-for="q in data.quarterly_financials.quarters" :key="q.period" class="px-4 py-1.5 text-right num">{{ fmtBigNum(q.total_debt) }}</td>
              </tr>
              <tr>
                <td class="px-4 py-1.5 text-muted">Ozkaynak</td>
                <td v-for="q in data.quarterly_financials.quarters" :key="q.period" class="px-4 py-1.5 text-right num">{{ fmtBigNum(q.total_equity) }}</td>
              </tr>
              <tr>
                <td class="px-4 py-1.5 text-muted">FCF</td>
                <td v-for="q in data.quarterly_financials.quarters" :key="q.period" class="px-4 py-1.5 text-right num" :class="pctClass(q.free_cash_flow)">{{ fmtBigNum(q.free_cash_flow) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="px-5 py-6 text-center text-sm text-faint">Ceyreklik finansal verisi bulunamadi.</p>
      </section>

      <!-- 2. KAP Bildirimleri -->
      <section class="card overflow-hidden">
        <h2 class="border-b border-border px-5 py-3 text-sm font-semibold uppercase tracking-wide text-muted">
          KAP Bildirimleri
        </h2>
        <div v-if="market === 'bist' && data.kap" class="p-5 space-y-3">
          <div v-if="data.kap.financial_periods?.length" class="flex flex-wrap gap-1.5">
            <span
              v-for="fp in data.kap.financial_periods"
              :key="fp"
              class="rounded-md bg-surface-2 px-2 py-0.5 text-[11px] font-medium text-muted"
            >{{ fp }}</span>
          </div>
          <ul v-if="data.kap.disclosures?.length" class="space-y-1.5">
            <li v-for="(d, i) in data.kap.disclosures" :key="i" class="flex gap-2 text-sm text-text/80">
              <span class="mt-0.5 text-accent">&#8226;</span>
              <span>{{ d }}</span>
            </li>
          </ul>
          <p v-if="!data.kap.disclosures?.length && !data.kap.financial_periods?.length" class="text-sm text-faint">
            KAP bildirimi bulunamadi.
          </p>
        </div>
        <p v-else class="px-5 py-6 text-center text-sm text-faint">
          KAP bilgisi yok (sadece BIST hisseleri icin gecerlidir).
        </p>
      </section>

      <!-- 3. Teknik Gostergeler -->
      <section class="card overflow-hidden">
        <h2 class="border-b border-border px-5 py-3 text-sm font-semibold uppercase tracking-wide text-muted">
          Teknik Gostergeler
        </h2>
        <div v-if="data.technicals" class="grid gap-4 p-5 md:grid-cols-2">
          <div v-for="(group, gKey) in indicatorGroups" :key="gKey" class="card-2 p-3">
            <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">{{ group.label }}</h3>
            <div class="space-y-1">
              <div v-for="ind in group.keys" :key="ind.key" class="flex justify-between text-sm">
                <span class="text-muted">{{ ind.label }}</span>
                <span class="num font-medium">{{ fmtNum(data.technicals.indicators[ind.key], 4) }}</span>
              </div>
            </div>
          </div>
        </div>
        <p v-else class="px-5 py-6 text-center text-sm text-faint">Teknik gosterge verisi bulunamadi.</p>
      </section>
    </template>
  </div>
</template>
