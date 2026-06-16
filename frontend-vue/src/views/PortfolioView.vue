<script setup lang="ts">
import { computed } from "vue";
import { usePanelStore } from "@/stores/panel";
import { ACTION_META } from "@/types";
import AllocationDonut from "@/components/AllocationDonut.vue";

const panel = usePanelStore();
const p = computed(() => panel.portfolio);
const positions = computed(() => p.value?.positions ?? []);
const cashPct = computed(() =>
  p.value && p.value.total_capital ? (p.value.cash_remaining / p.value.total_capital) * 100 : 100
);
const bySector = computed(() => {
  const m: Record<string, number> = {};
  for (const pos of positions.value) m[pos.sector || "—"] = (m[pos.sector || "—"] ?? 0) + pos.allocation_weight;
  return Object.entries(m).sort((a, b) => b[1] - a[1]);
});
function tone(sig: keyof typeof ACTION_META) {
  return { bull: "bg-bull/12 text-bull", bear: "bg-bear/12 text-bear", watch: "bg-watch/12 text-watch" }[ACTION_META[sig].tone];
}
</script>

<template>
  <section v-if="p" class="grid grid-cols-12 gap-4">
    <!-- KPIs -->
    <div class="col-span-6 sm:col-span-3 card p-4"><div class="text-[11px] text-muted">Pozisyon</div><div class="num mt-1 text-2xl font-semibold">{{ p.allocated_count }}</div></div>
    <div class="col-span-6 sm:col-span-3 card p-4"><div class="text-[11px] text-muted">Yatırılan</div><div class="num mt-1 text-2xl font-semibold">{{ (100 - cashPct).toFixed(0) }}%</div></div>
    <div class="col-span-6 sm:col-span-3 card p-4"><div class="text-[11px] text-muted">Nakit</div><div class="num mt-1 text-2xl font-semibold text-muted">{{ cashPct.toFixed(0) }}%</div></div>
    <div class="col-span-6 sm:col-span-3 card p-4"><div class="text-[11px] text-muted">Sermaye</div><div class="num mt-1 text-2xl font-semibold">${{ p.total_capital.toLocaleString() }}</div></div>

    <!-- donut -->
    <section class="col-span-12 lg:col-span-4 card p-5">
      <h2 class="mb-2 text-sm font-semibold">Dağılım</h2>
      <AllocationDonut :positions="positions" :cash-pct="cashPct" />
    </section>

    <!-- sector exposure -->
    <section class="col-span-12 lg:col-span-8 card p-5">
      <h2 class="mb-3 text-sm font-semibold">Sektör Dağılımı</h2>
      <div v-if="bySector.length" class="space-y-2.5">
        <div v-for="[sec, w] in bySector" :key="sec" class="flex items-center gap-3 text-xs">
          <span class="w-36 shrink-0 truncate text-muted">{{ sec }}</span>
          <div class="h-2.5 flex-1 overflow-hidden rounded-full bg-surface-3">
            <div class="h-full rounded-full bg-gradient-to-r from-accent/70 to-accent" :style="{ width: Math.min(100, w) + '%' }" />
          </div>
          <span class="num w-10 text-right">{{ w.toFixed(0) }}%</span>
        </div>
      </div>
      <div v-else class="py-8 text-center text-sm text-muted">Aksiyon pozisyonu yok</div>
    </section>

    <!-- table -->
    <section class="col-span-12 card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-surface-2 text-left text-[11px] uppercase tracking-wide text-muted">
          <tr>
            <th class="px-5 py-3">Hisse</th><th class="px-5 py-3">Sektör</th><th class="px-5 py-3">Aksiyon</th>
            <th class="px-5 py-3 text-right">Güven</th><th class="px-5 py-3 text-right">Ağırlık</th><th class="px-5 py-3 text-right">Tutar</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="pos in positions" :key="pos.ticker" class="border-t border-border transition hover:bg-surface-2">
            <td class="num px-5 py-3 font-medium">{{ pos.ticker }}</td>
            <td class="px-5 py-3 text-muted">{{ pos.sector }}</td>
            <td class="px-5 py-3"><span class="rounded-md px-2 py-0.5 text-xs" :class="tone(pos.signal)">{{ ACTION_META[pos.signal].label }}</span></td>
            <td class="num px-5 py-3 text-right">{{ Math.round(pos.confidence * 100) }}%</td>
            <td class="num px-5 py-3 text-right">{{ pos.allocation_weight.toFixed(1) }}%</td>
            <td class="num px-5 py-3 text-right">${{ pos.allocation_cash.toLocaleString() }}</td>
          </tr>
          <tr v-if="!positions.length"><td colspan="6" class="px-5 py-10 text-center text-muted">Aksiyon pozisyonu yok (hepsi nakit).</td></tr>
        </tbody>
      </table>
    </section>
  </section>
  <div v-else class="py-20 text-center text-muted">Portföy verisi yok.</div>
</template>
