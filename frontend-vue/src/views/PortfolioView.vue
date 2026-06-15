<script setup lang="ts">
import { computed } from "vue";
import { usePanelStore } from "@/stores/panel";
import { ACTION_META } from "@/types";

const panel = usePanelStore();
const p = computed(() => panel.portfolio);
const positions = computed(() => p.value?.positions ?? []);
const cashPct = computed(() =>
  p.value && p.value.total_capital ? (p.value.cash_remaining / p.value.total_capital) * 100 : 100
);

// sector exposure for the bar
const bySector = computed(() => {
  const m: Record<string, number> = {};
  for (const pos of positions.value) m[pos.sector || "—"] = (m[pos.sector || "—"] ?? 0) + pos.allocation_weight;
  return Object.entries(m).sort((a, b) => b[1] - a[1]);
});
</script>

<template>
  <section v-if="p">
    <div class="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div class="stat"><div class="stat-v">{{ p.allocated_count }}</div><div class="stat-l">Pozisyon</div></div>
      <div class="stat"><div class="stat-v">{{ (100 - cashPct).toFixed(0) }}%</div><div class="stat-l">Yatırılan</div></div>
      <div class="stat"><div class="stat-v">{{ cashPct.toFixed(0) }}%</div><div class="stat-l">Nakit</div></div>
      <div class="stat"><div class="stat-v">${{ p.total_capital.toLocaleString() }}</div><div class="stat-l">Sermaye</div></div>
    </div>

    <!-- sector exposure -->
    <div v-if="bySector.length" class="mb-5 rounded-xl border border-border bg-surface p-4">
      <div class="mb-2 text-xs text-muted">Sektör dağılımı</div>
      <div class="space-y-2">
        <div v-for="[sec, w] in bySector" :key="sec" class="flex items-center gap-3 text-xs">
          <span class="w-40 shrink-0 truncate text-muted">{{ sec }}</span>
          <div class="h-2 flex-1 overflow-hidden rounded-full bg-surface-2">
            <div class="h-full rounded-full bg-accent" :style="{ width: Math.min(100, w) + '%' }" />
          </div>
          <span class="w-10 text-right">{{ w.toFixed(0) }}%</span>
        </div>
      </div>
    </div>

    <div v-if="!positions.length" class="py-16 text-center text-muted">Aksiyon alınabilir pozisyon yok (hepsi nakit).</div>
    <div v-else class="overflow-hidden rounded-xl border border-border">
      <table class="w-full text-sm">
        <thead class="bg-surface-2 text-left text-xs text-muted">
          <tr>
            <th class="px-4 py-2.5">Hisse</th><th class="px-4 py-2.5">Sektör</th>
            <th class="px-4 py-2.5">Aksiyon</th><th class="px-4 py-2.5 text-right">Güven</th>
            <th class="px-4 py-2.5 text-right">Ağırlık</th><th class="px-4 py-2.5 text-right">Tutar</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="pos in positions" :key="pos.ticker" class="border-t border-border bg-surface hover:bg-surface-2">
            <td class="px-4 py-2.5 font-medium">{{ pos.ticker }}</td>
            <td class="px-4 py-2.5 text-muted">{{ pos.sector }}</td>
            <td class="px-4 py-2.5">
              <span class="rounded px-1.5 py-0.5 text-xs"
                :class="ACTION_META[pos.signal].tone === 'bull' ? 'bg-bull/15 text-bull' : ACTION_META[pos.signal].tone === 'bear' ? 'bg-bear/15 text-bear' : 'bg-watch/15 text-watch'">
                {{ ACTION_META[pos.signal].label }}
              </span>
            </td>
            <td class="px-4 py-2.5 text-right">{{ Math.round(pos.confidence * 100) }}%</td>
            <td class="px-4 py-2.5 text-right">{{ pos.allocation_weight.toFixed(1) }}%</td>
            <td class="px-4 py-2.5 text-right">${{ pos.allocation_cash.toLocaleString() }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
  <div v-else class="py-16 text-center text-muted">Portföy verisi yok.</div>
</template>
