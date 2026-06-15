<script setup lang="ts">
import { onMounted } from "vue";
import { RouterLink, RouterView } from "vue-router";
import { usePanelStore } from "@/stores/panel";

const panel = usePanelStore();
onMounted(() => panel.load());
</script>

<template>
  <div class="min-h-screen">
    <header class="sticky top-0 z-10 border-b border-border bg-bg/80 backdrop-blur">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-5 py-3.5">
        <div class="flex items-center gap-3">
          <div class="grid h-8 w-8 place-items-center rounded-lg bg-accent/15 text-accent font-bold">F</div>
          <div>
            <div class="text-sm font-semibold tracking-tight">FinLLM</div>
            <div class="text-[11px] text-muted">Karar Paneli</div>
          </div>
        </div>

        <nav class="flex items-center gap-1 rounded-lg bg-surface p-1 text-sm">
          <RouterLink to="/signals"
            class="rounded-md px-3 py-1.5 text-muted transition hover:text-white"
            active-class="!bg-surface-2 !text-white">Sinyaller</RouterLink>
          <RouterLink to="/portfolio"
            class="rounded-md px-3 py-1.5 text-muted transition hover:text-white"
            active-class="!bg-surface-2 !text-white">Portföy</RouterLink>
        </nav>

        <div class="flex items-center gap-2">
          <div class="flex rounded-lg bg-surface p-1 text-xs">
            <button
              v-for="m in (['nasdaq','bist'] as const)" :key="m"
              class="rounded-md px-2.5 py-1 capitalize transition"
              :class="panel.market === m ? 'bg-accent/20 text-accent' : 'text-muted hover:text-white'"
              @click="panel.setMarket(m)"
            >{{ m === 'nasdaq' ? 'ABD' : 'BIST' }}</button>
          </div>
          <button
            class="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-muted hover:text-white disabled:opacity-50"
            :disabled="panel.loading" @click="panel.load()"
          >{{ panel.loading ? 'Yükleniyor…' : 'Yenile' }}</button>
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-6xl px-5 py-6">
      <div v-if="panel.error" class="mb-5 rounded-xl border border-bear/30 bg-bear/10 px-4 py-3 text-sm text-bear">
        Backend ulaşılamıyor: {{ panel.error }}
        <div class="mt-1 text-xs text-muted">
          panel_server'ı çalıştır: <code>uvicorn finllm.api.panel_server:app --port 8000</code>
        </div>
      </div>
      <RouterView />
    </main>
  </div>
</template>
