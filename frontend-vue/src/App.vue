<script setup lang="ts">
import { onMounted } from "vue";
import { RouterLink, RouterView } from "vue-router";
import { usePanelStore } from "@/stores/panel";
import SignalDetail from "@/components/SignalDetail.vue";

const panel = usePanelStore();
onMounted(() => panel.load());
</script>

<template>
  <div class="min-h-screen">
    <header class="sticky top-0 z-20 border-b border-border bg-bg/85 backdrop-blur-md">
      <div class="mx-auto flex max-w-7xl items-center justify-between px-5 py-3">
        <div class="flex items-center gap-3">
          <div class="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-accent/30 to-accent/5 text-accent font-bold ring-1 ring-accent/20">F</div>
          <div>
            <div class="text-sm font-semibold tracking-tight">FinLLM <span class="text-faint">·</span> <span class="text-muted">Karar Paneli</span></div>
            <div class="num text-[10px] text-faint">{{ panel.signals?.summary.run_id ?? '—' }}</div>
          </div>
        </div>

        <nav class="flex items-center gap-1 rounded-xl border border-border bg-surface p-1 text-sm">
          <RouterLink v-for="t in [['/overview','Genel'],['/signals','Sinyaller'],['/portfolio','Portföy']]" :key="t[0]"
            :to="t[0]" class="rounded-lg px-3.5 py-1.5 text-muted transition hover:text-white"
            active-class="!bg-surface-3 !text-white">{{ t[1] }}</RouterLink>
        </nav>

        <div class="flex items-center gap-2">
          <div class="flex rounded-xl border border-border bg-surface p-1 text-xs">
            <button v-for="m in (['nasdaq','bist'] as const)" :key="m"
              class="rounded-lg px-3 py-1.5 transition"
              :class="panel.market === m ? 'bg-accent/15 text-accent' : 'text-muted hover:text-white'"
              @click="panel.setMarket(m)">{{ m === 'nasdaq' ? 'ABD' : 'BIST' }}</button>
          </div>
          <button class="rounded-xl border border-border bg-surface px-3 py-2 text-xs text-muted transition hover:text-white disabled:opacity-50"
            :disabled="panel.loading" @click="panel.load()">
            <span :class="{ 'inline-block animate-spin': panel.loading }">↻</span>
          </button>
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-7xl px-5 py-6">
      <div v-if="panel.error" class="mb-5 rounded-xl border border-bear/30 bg-bear/10 px-4 py-3 text-sm text-bear">
        Backend ulaşılamıyor: {{ panel.error }}
        <div class="mt-1 text-xs text-muted">panel_server: <code class="num">uvicorn finllm.api.panel_server:app --port 8000</code></div>
      </div>
      <RouterView />
    </main>

    <SignalDetail :signal="panel.selected" @close="panel.selected = null" />
  </div>
</template>
