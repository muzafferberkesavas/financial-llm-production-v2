<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import type { BistStock } from "@/types";
import { fetchBistStocks } from "@/lib/api";

const router = useRouter();
const stocks = ref<BistStock[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const search = ref("");
const selectedSector = ref("");

onMounted(async () => {
  try {
    const res = await fetchBistStocks();
    stocks.value = res.stocks;
  } catch (e: any) {
    error.value = e.message ?? "Veri yuklenemedi";
  } finally {
    loading.value = false;
  }
});

const sectors = computed(() => {
  const set = new Set(stocks.value.map((s) => s.sector).filter(Boolean));
  return [...set].sort();
});

const filtered = computed(() => {
  let list = stocks.value;
  if (selectedSector.value) {
    list = list.filter((s) => s.sector === selectedSector.value);
  }
  if (search.value) {
    const q = search.value.toUpperCase();
    list = list.filter(
      (s) => s.symbol.includes(q) || s.name.toUpperCase().includes(q)
    );
  }
  return list;
});

function goToDetail(symbol: string) {
  router.push({ name: "stock-detail", params: { ticker: symbol }, query: { market: "bist" } });
}
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center gap-3">
      <h1 class="text-xl font-bold tracking-tight">BIST Hisseleri</h1>
      <span class="rounded-md bg-surface-2 px-2 py-0.5 text-xs text-muted">{{ filtered.length }} hisse</span>
    </div>

    <!-- Filtreler -->
    <div class="flex flex-wrap gap-3">
      <input
        v-model="search"
        type="text"
        placeholder="Sembol veya isim ara..."
        class="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text placeholder-faint outline-none focus:border-accent"
      />
      <select
        v-model="selectedSector"
        class="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text outline-none focus:border-accent"
      >
        <option value="">Tum Sektorler</option>
        <option v-for="sec in sectors" :key="sec" :value="sec">{{ sec }}</option>
      </select>
    </div>

    <!-- Loading / Error -->
    <div v-if="loading" class="py-12 text-center text-muted">Yukleniyor...</div>
    <div v-else-if="error" class="rounded-xl border border-bear/30 bg-bear/5 p-4 text-sm text-bear">{{ error }}</div>

    <!-- Hisse tablosu -->
    <div v-else class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-border text-left text-xs text-faint">
            <th class="px-4 py-2.5">Sembol</th>
            <th class="px-4 py-2.5">Sirket</th>
            <th class="px-4 py-2.5">Sektor</th>
            <th class="px-4 py-2.5"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border/50">
          <tr
            v-for="s in filtered"
            :key="s.symbol"
            class="cursor-pointer transition hover:bg-surface-2"
            @click="goToDetail(s.symbol)"
          >
            <td class="px-4 py-2.5 num font-semibold">{{ s.symbol }}</td>
            <td class="px-4 py-2.5 text-text/80">{{ s.name }}</td>
            <td class="px-4 py-2.5">
              <span class="rounded-md bg-surface-2 px-2 py-0.5 text-[11px] text-muted">{{ s.sector }}</span>
            </td>
            <td class="px-4 py-2.5 text-right text-xs text-muted">Detay &rarr;</td>
          </tr>
          <tr v-if="!filtered.length">
            <td colspan="4" class="px-4 py-8 text-center text-faint">Sonuc bulunamadi.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
