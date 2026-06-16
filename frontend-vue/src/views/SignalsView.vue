<script setup lang="ts">
import { computed, ref } from "vue";
import { usePanelStore } from "@/stores/panel";
import SignalCard from "@/components/SignalCard.vue";
import type { ExtendedSignal } from "@/types";

const panel = usePanelStore();
const onlyActionable = ref(false);
const signals = computed(() =>
  onlyActionable.value ? panel.list.filter((s) => s.is_actionable) : panel.list
);

function open(s: ExtendedSignal) { panel.selected = s; }
</script>

<template>
  <section>
    <div class="mb-4 flex items-center justify-between">
      <div class="text-sm text-muted">
        <span class="num font-medium text-text">{{ panel.list.length }}</span> sinyal ·
        <span class="num font-medium text-bull">{{ panel.actionable.length }}</span> aksiyon
      </div>
      <label class="flex cursor-pointer items-center gap-2 text-xs text-muted">
        <input type="checkbox" v-model="onlyActionable" class="accent-accent" />
        Sadece aksiyon alınabilir
      </label>
    </div>

    <!-- skeleton -->
    <div v-if="panel.loading && !panel.list.length" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="i in 6" :key="i" class="card skeleton h-48" />
    </div>

    <div v-else-if="!signals.length" class="py-20 text-center text-muted">
      <div class="text-sm">Sinyal yok.</div>
      <div class="mt-1 text-xs">Panel çalıştır: <code class="num">run_decision_panel.py --top-n 4 --export</code></div>
    </div>

    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <SignalCard v-for="sig in signals" :key="sig.ticker" :signal="sig" @open="open" />
    </div>
  </section>
</template>
