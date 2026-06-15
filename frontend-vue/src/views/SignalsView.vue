<script setup lang="ts">
import { computed } from "vue";
import { usePanelStore } from "@/stores/panel";
import SignalCard from "@/components/SignalCard.vue";

const panel = usePanelStore();
const signals = computed(() => panel.signals?.signals ?? []);
const summary = computed(() => panel.signals?.summary);
</script>

<template>
  <section>
    <!-- summary strip -->
    <div v-if="summary" class="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div class="stat"><div class="stat-v">{{ summary.signals_generated }}</div><div class="stat-l">Sinyal</div></div>
      <div class="stat"><div class="stat-v text-bull">{{ summary.actionable_signals }}</div><div class="stat-l">Aksiyon</div></div>
      <div class="stat"><div class="stat-v capitalize">{{ summary.regime?.fear_level || summary.mode }}</div><div class="stat-l">Rejim</div></div>
      <div class="stat"><div class="stat-v">${{ summary.total_cost_usd.toFixed(3) }}</div><div class="stat-l">LLM maliyeti</div></div>
    </div>

    <div v-if="panel.loading && !signals.length" class="py-16 text-center text-muted">Yükleniyor…</div>
    <div v-else-if="!signals.length" class="py-16 text-center text-muted">
      Henüz sinyal yok.
      <div class="mt-1 text-xs">Panel çalıştır: <code>run_decision_panel.py --top-n 4 --export</code></div>
    </div>

    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <SignalCard v-for="s in signals" :key="s.ticker" :signal="s" />
    </div>
  </section>
</template>
