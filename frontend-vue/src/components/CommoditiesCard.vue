<script setup lang="ts">
import { computed } from "vue";
import { usePanelStore } from "@/stores/panel";

const panel = usePanelStore();
const items = computed(() => panel.commodities?.instruments ?? []);
// Macro appetite for the precious-metals leg (drives the gold thesis).
const goldAppetite = computed(() =>
  panel.macro?.sectors.find((s) => s.sector === "Precious Metals")?.appetite ?? null
);

function chgClass(v?: number | null) {
  if (v == null) return "text-muted";
  return v > 0 ? "text-bull" : v < 0 ? "text-bear" : "text-muted";
}
function fmt(p: number) {
  const dec = p >= 1000 ? 0 : 2;
  return p.toLocaleString("tr-TR", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}
const isGold = (k: string) => k.startsWith("gold");
</script>

<template>
  <section class="card p-5">
    <div class="mb-3 flex items-center justify-between">
      <h2 class="text-sm font-semibold">Altın & Emtia</h2>
      <span v-if="goldAppetite != null" class="rounded-md px-2 py-0.5 text-[11px]"
        :class="goldAppetite >= 0.55 ? 'bg-bull/12 text-bull' : goldAppetite <= 0.45 ? 'bg-bear/12 text-bear' : 'bg-watch/12 text-watch'">
        makro iştah {{ goldAppetite.toFixed(2) }}
      </span>
    </div>

    <div v-if="items.length" class="space-y-2">
      <div v-for="it in items" :key="it.key"
        class="flex items-center justify-between rounded-lg px-3 py-2.5"
        :class="isGold(it.key) ? 'bg-watch/8 ring-1 ring-watch/15' : 'bg-surface-2'">
        <div class="flex items-center gap-2">
          <span v-if="isGold(it.key)" class="text-watch">◆</span>
          <span class="text-sm" :class="isGold(it.key) ? 'font-medium text-text' : 'text-muted'">{{ it.label }}</span>
        </div>
        <div class="flex items-center gap-3 text-right">
          <div>
            <span class="num text-sm font-medium">{{ fmt(it.price) }}</span>
            <span class="ml-1 text-[10px] text-faint">{{ it.unit }}</span>
          </div>
          <span class="num w-14 text-right text-xs" :class="chgClass(it.change_5d_pct)">
            {{ it.change_5d_pct != null ? (it.change_5d_pct > 0 ? '+' : '') + it.change_5d_pct.toFixed(1) + '%' : '—' }}
          </span>
        </div>
      </div>
      <div class="pt-1 text-right text-[10px] text-faint">5g değişim · {{ panel.commodities?.as_of }}</div>
    </div>
    <div v-else class="py-8 text-center text-sm text-muted">Emtia verisi yok</div>
  </section>
</template>
