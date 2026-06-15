import { defineStore } from "pinia";
import { ref } from "vue";
import { fetchSignals, fetchPortfolio } from "@/lib/api";
import type { SignalsResponse, PortfolioResponse, Market } from "@/types";

export const usePanelStore = defineStore("panel", () => {
  const market = ref<Market>("nasdaq");
  const signals = ref<SignalsResponse | null>(null);
  const portfolio = ref<PortfolioResponse | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function load() {
    loading.value = true;
    error.value = null;
    try {
      const [s, p] = await Promise.allSettled([
        fetchSignals(market.value),
        fetchPortfolio(market.value),
      ]);
      signals.value = s.status === "fulfilled" ? s.value : null;
      portfolio.value = p.status === "fulfilled" ? p.value : null;
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

  return { market, signals, portfolio, loading, error, load, setMarket };
});
