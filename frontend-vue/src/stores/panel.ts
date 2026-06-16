import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { fetchSignals, fetchPortfolio, fetchCommodities } from "@/lib/api";
import type { SignalsResponse, PortfolioResponse, CommoditiesResponse, Market, ExtendedSignal, MacroBlock } from "@/types";

export const usePanelStore = defineStore("panel", () => {
  const market = ref<Market>("nasdaq");
  const signals = ref<SignalsResponse | null>(null);
  const portfolio = ref<PortfolioResponse | null>(null);
  const commodities = ref<CommoditiesResponse | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const selected = ref<ExtendedSignal | null>(null);

  const macro = computed<MacroBlock | null>(() => signals.value?.summary.macro ?? null);
  const list = computed<ExtendedSignal[]>(() => signals.value?.signals ?? []);
  const actionable = computed(() => list.value.filter((s) => s.is_actionable));

  async function load() {
    loading.value = true;
    error.value = null;
    try {
      const [s, p, c] = await Promise.allSettled([
        fetchSignals(market.value),
        fetchPortfolio(market.value),
        fetchCommodities(),
      ]);
      signals.value = s.status === "fulfilled" ? s.value : null;
      portfolio.value = p.status === "fulfilled" ? p.value : null;
      commodities.value = c.status === "fulfilled" ? c.value : null;
      if (s.status === "rejected" && p.status === "rejected") {
        error.value = String((s.reason as Error)?.message ?? "Backend ulaşılamıyor");
      }
    } catch (e) {
      error.value = (e as Error).message;
    } finally {
      loading.value = false;
    }
  }

  function setMarket(m: Market) {
    market.value = m;
    void load();
  }

  return {
    market, signals, portfolio, commodities, loading, error, selected,
    macro, list, actionable, load, setMarket,
  };
});
