<script setup lang="ts">
import { computed } from "vue";
import { usePanelStore } from "@/stores/panel";
import SectorHeatStrip from "@/components/SectorHeatStrip.vue";
import AllocationDonut from "@/components/AllocationDonut.vue";
import ActionBadge from "@/components/ActionBadge.vue";
import CommoditiesCard from "@/components/CommoditiesCard.vue";

const panel = usePanelStore();
const s = computed(() => panel.signals?.summary);
const macro = computed(() => panel.macro);
const port = computed(() => panel.portfolio);
const cashPct = computed(() =>
  port.value && port.value.total_capital ? (port.value.cash_remaining / port.value.total_capital) * 100 : 100
);
const stanceMeta = computed(() => {
  const st = macro.value?.stance ?? "";
  if (st === "risk_on") return { label: "RISK-ON", cls: "text-bull", dot: "bg-bull" };
  if (st === "risk_off") return { label: "RISK-OFF", cls: "text-bear", dot: "bg-bear" };
  return { label: "NÖTR", cls: "text-watch", dot: "bg-watch" };
});
const topSignals = computed(() =>
  [...panel.list].sort((a, b) => b.confluence_score - a.confluence_score).slice(0, 6)
);
</script>

<template>
  <div class="grid grid-cols-12 gap-4">
    <!-- KPI row -->
    <div class="col-span-6 sm:col-span-3 card p-4">
      <div class="text-[11px] text-muted">Aksiyon Sinyali</div>
      <div class="num mt-1 text-3xl font-semibold text-bull">{{ s?.actionable_signals ?? 0 }}<span class="text-base text-faint">/{{ s?.signals_generated ?? 0 }}</span></div>
    </div>
    <div class="col-span-6 sm:col-span-3 card p-4">
      <div class="text-[11px] text-muted">Yatırılan</div>
      <div class="num mt-1 text-3xl font-semibold">{{ (100 - cashPct).toFixed(0) }}<span class="text-base text-faint">%</span></div>
    </div>
    <div class="col-span-6 sm:col-span-3 card p-4">
      <div class="text-[11px] text-muted">Piyasa Rejimi</div>
      <div class="mt-1.5 flex items-center gap-2">
        <span class="h-2 w-2 rounded-full" :class="stanceMeta.dot" />
        <span class="text-xl font-semibold" :class="stanceMeta.cls">{{ stanceMeta.label }}</span>
      </div>
    </div>
    <div class="col-span-6 sm:col-span-3 card p-4">
      <div class="text-[11px] text-muted">LLM Maliyeti</div>
      <div class="num mt-1 text-3xl font-semibold">${{ (s?.total_cost_usd ?? 0).toFixed(3) }}</div>
    </div>

    <!-- Macro → sector heatmap (signature, large) -->
    <section class="col-span-12 lg:col-span-8 card p-5">
      <div class="mb-1 flex items-center justify-between">
        <h2 class="text-sm font-semibold">Makro → Sektör İştahı</h2>
        <span class="text-[11px] text-muted">0 = ayı · 0.5 = nötr · 1 = boğa</span>
      </div>
      <p v-if="macro?.summary" class="mb-3 line-clamp-2 text-xs text-muted">{{ macro.summary }}</p>
      <SectorHeatStrip v-if="macro?.sectors.length" :sectors="macro.sectors" />
      <div v-else class="py-10 text-center text-sm text-muted">Makro verisi yok</div>
    </section>

    <!-- Gold & commodities -->
    <div class="col-span-12 lg:col-span-4">
      <CommoditiesCard />
    </div>

    <!-- Allocation donut -->
    <section class="col-span-12 lg:col-span-5 card p-5">
      <h2 class="mb-2 text-sm font-semibold">Portföy Tahsisi</h2>
      <AllocationDonut v-if="port" :positions="port.positions" :cash-pct="cashPct" />
      <div v-else class="py-10 text-center text-sm text-muted">Portföy verisi yok</div>
      <div v-if="port" class="mt-2 space-y-1.5">
        <div v-for="p in port.positions" :key="p.ticker" class="flex items-center justify-between text-xs">
          <span class="num font-medium">{{ p.ticker }}</span>
          <span class="num text-muted">{{ p.allocation_weight.toFixed(1) }}% · ${{ p.allocation_cash.toLocaleString() }}</span>
        </div>
        <div class="flex items-center justify-between border-t border-border pt-1.5 text-xs text-muted">
          <span>Nakit</span><span class="num">{{ cashPct.toFixed(0) }}%</span>
        </div>
      </div>
    </section>

    <!-- Top signals strip -->
    <section class="col-span-12 card p-5">
      <h2 class="mb-3 text-sm font-semibold">En Yüksek Öncelikli Sinyaller</h2>
      <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        <button v-for="sig in topSignals" :key="sig.ticker"
          class="card-2 flex items-center justify-between px-3.5 py-2.5 text-left transition hover:border-border-2"
          @click="panel.selected = sig">
          <div class="flex items-center gap-2.5">
            <span class="num font-semibold">{{ sig.ticker }}</span>
            <ActionBadge :action="sig.signal" size="sm" />
          </div>
          <div class="flex items-center gap-3 text-xs">
            <span class="num text-muted">{{ Math.round(sig.confidence * 100) }}%</span>
            <span class="num w-10 text-right" :class="sig.allocation_weight > 0 ? '' : 'text-faint'">
              {{ sig.allocation_weight > 0 ? sig.allocation_weight.toFixed(1) + '%' : '—' }}
            </span>
          </div>
        </button>
      </div>
    </section>
  </div>
</template>
