<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import {
  fetchQuote,
  fetchNotebookEntries,
  addNotebookEntry,
  updateNotebookNote,
  updateNotebookPrices,
  deleteNotebookEntry,
} from "@/lib/api";
import type { NotebookEntry } from "@/lib/api";

const entries = ref<NotebookEntry[]>([]);
const tickerInput = ref("");
const adding = ref(false);
const addError = ref<string | null>(null);
const refreshing = ref(false);
const loading = ref(true);

onMounted(async () => {
  try {
    entries.value = await fetchNotebookEntries();
  } catch { /* empty */ }
  loading.value = false;
  refreshAll();
});

// Auto-refresh every 60s
let timer: ReturnType<typeof setInterval> | null = null;
onMounted(() => {
  timer = setInterval(refreshAll, 60_000);
});
onUnmounted(() => {
  if (timer) clearInterval(timer);
});

async function addEntry() {
  const raw = tickerInput.value.trim().toUpperCase();
  if (!raw) return;

  const ticker = raw.replace(/\.IS$/, "");

  if (entries.value.some(e => e.ticker === ticker)) {
    addError.value = `${ticker} zaten defterde`;
    return;
  }

  adding.value = true;
  addError.value = null;

  try {
    const q = await fetchQuote(ticker);
    if (q.error) {
      addError.value = `${ticker}: ${q.error}`;
      return;
    }
    const entry: NotebookEntry = {
      id: Date.now().toString(36),
      ticker,
      note: "",
      entryPrice: q.price,
      entryDate: q.as_of,
      currentPrice: q.price,
      currentDate: q.as_of,
      addedAt: new Date().toISOString(),
    };
    await addNotebookEntry(entry);
    entries.value.unshift(entry);
    tickerInput.value = "";
  } catch (e: any) {
    addError.value = e.message ?? "Fiyat alinamadi";
  } finally {
    adding.value = false;
  }
}

async function removeEntry(id: string) {
  try {
    await deleteNotebookEntry(id);
    entries.value = entries.value.filter(e => e.id !== id);
  } catch { /* ignore */ }
}

let noteTimer: ReturnType<typeof setTimeout> | null = null;
function onNoteInput(id: string, note: string) {
  const entry = entries.value.find(e => e.id === id);
  if (entry) entry.note = note;
  // Debounce save
  if (noteTimer) clearTimeout(noteTimer);
  noteTimer = setTimeout(() => {
    updateNotebookNote(id, note).catch(() => {});
  }, 500);
}

async function refreshAll() {
  if (!entries.value.length) return;
  refreshing.value = true;
  try {
    const priceUpdates: Record<string, { currentPrice: number; currentDate: string }> = {};
    const promises = entries.value.map(async (entry) => {
      try {
        const q = await fetchQuote(entry.ticker);
        if (!q.error) {
          entry.currentPrice = q.price;
          entry.currentDate = q.as_of;
          priceUpdates[entry.id] = { currentPrice: q.price, currentDate: q.as_of };
        }
      } catch { /* skip */ }
    });
    await Promise.all(promises);
    if (Object.keys(priceUpdates).length) {
      await updateNotebookPrices(priceUpdates).catch(() => {});
    }
  } finally {
    refreshing.value = false;
  }
}

function changePct(entry: NotebookEntry): number | null {
  if (entry.currentPrice == null || !entry.entryPrice) return null;
  return ((entry.currentPrice - entry.entryPrice) / entry.entryPrice) * 100;
}

function fmtPct(val: number | null): string {
  if (val == null) return "—";
  const sign = val >= 0 ? "+" : "";
  return `${sign}${val.toFixed(2)}%`;
}

function fmtPrice(val: number | null): string {
  if (val == null) return "—";
  return val.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("tr-TR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch { return iso; }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="text-xl font-bold tracking-tight">Analiz Defteri</h1>
        <p class="text-xs text-muted mt-1">
          Hisse ekle, giris fiyatini kaydet, degisimi takip et, not al
        </p>
      </div>
      <button
        class="rounded-lg border border-border bg-surface px-4 py-2 text-xs text-muted transition hover:text-white disabled:opacity-50"
        :disabled="refreshing || !entries.length"
        @click="refreshAll"
      >
        <span :class="{ 'inline-block animate-spin': refreshing }">↻</span>
        Fiyatlari Guncelle
      </button>
    </div>

    <!-- Add new entry -->
    <div class="card p-4">
      <div class="flex items-center gap-3">
        <input
          v-model="tickerInput"
          type="text"
          placeholder="Sembol gir (ornek: THYAO, GARAN, ASELS)"
          class="flex-1 rounded-lg border border-border bg-surface px-4 py-2.5 text-sm text-text outline-none placeholder:text-faint focus:border-accent/50 focus:ring-1 focus:ring-accent/30"
          @keyup.enter="addEntry"
          :disabled="adding"
        />
        <button
          class="rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-accent/80 disabled:opacity-50"
          :disabled="adding || !tickerInput.trim()"
          @click="addEntry"
        >
          <span v-if="adding" class="inline-flex items-center gap-2">
            <span class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
          </span>
          <span v-else>Ekle</span>
        </button>
      </div>
      <p v-if="addError" class="mt-2 text-xs text-bear">{{ addError }}</p>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="card p-12 text-center">
      <span class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
    </div>

    <!-- Entries -->
    <div v-else-if="!entries.length" class="card p-12 text-center">
      <p class="text-muted mb-2">Defter bos</p>
      <p class="text-xs text-faint">Yukaridaki alana sembol yazarak hisse ekleyin</p>
    </div>

    <div v-for="entry in entries" :key="entry.id" class="card overflow-hidden">
      <div class="p-4">
        <!-- Ticker row -->
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-3">
            <span class="num text-lg font-bold">{{ entry.ticker }}</span>
            <span class="rounded-md bg-surface-2 px-2 py-0.5 text-[10px] text-faint">
              Eklendi: {{ fmtDate(entry.addedAt) }}
            </span>
          </div>
          <button
            class="rounded-lg p-1.5 text-faint hover:text-bear hover:bg-bear/10 transition"
            @click="removeEntry(entry.id)"
            title="Sil"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>

        <!-- Price cards -->
        <div class="grid grid-cols-3 gap-3 mb-3">
          <div class="rounded-xl border border-border bg-surface-2 p-3">
            <div class="text-[10px] text-faint uppercase">Giris Fiyati</div>
            <div class="num text-lg font-semibold">{{ fmtPrice(entry.entryPrice) }}</div>
            <div class="text-[10px] text-faint">{{ entry.entryDate }}</div>
          </div>
          <div class="rounded-xl border border-border bg-surface-2 p-3">
            <div class="text-[10px] text-faint uppercase">Guncel Fiyat</div>
            <div class="num text-lg font-semibold">{{ fmtPrice(entry.currentPrice) }}</div>
            <div class="text-[10px] text-faint">{{ entry.currentDate ?? '—' }}</div>
          </div>
          <div class="rounded-xl border p-3" :class="(changePct(entry) ?? 0) >= 0 ? 'border-bull/30 bg-bull/5' : 'border-bear/30 bg-bear/5'">
            <div class="text-[10px] text-faint uppercase">Degisim</div>
            <div class="num text-lg font-bold" :class="(changePct(entry) ?? 0) >= 0 ? 'text-bull' : 'text-bear'">
              {{ fmtPct(changePct(entry)) }}
            </div>
            <div class="num text-[10px]" :class="(changePct(entry) ?? 0) >= 0 ? 'text-bull/60' : 'text-bear/60'">
              {{ entry.currentPrice != null ? (entry.currentPrice - entry.entryPrice >= 0 ? '+' : '') + fmtPrice(entry.currentPrice - entry.entryPrice) : '—' }} TL
            </div>
          </div>
        </div>

        <!-- Note -->
        <textarea
          :value="entry.note"
          @input="onNoteInput(entry.id, ($event.target as HTMLTextAreaElement).value)"
          placeholder="Not ekle... (analiz, gozlem, strateji)"
          class="w-full rounded-xl border border-border bg-surface px-4 py-3 text-sm text-text outline-none placeholder:text-faint focus:border-accent/50 focus:ring-1 focus:ring-accent/30 resize-y min-h-[60px]"
          rows="2"
        />
      </div>
    </div>
  </div>
</template>
