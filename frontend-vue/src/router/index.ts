import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", redirect: "/overview" },
  { path: "/overview", name: "overview", component: () => import("@/views/OverviewView.vue") },
  { path: "/signals", name: "signals", component: () => import("@/views/SignalsView.vue") },
  { path: "/portfolio", name: "portfolio", component: () => import("@/views/PortfolioView.vue") },
  { path: "/bist", name: "bist-stocks", component: () => import("@/views/BistStocksView.vue") },
  { path: "/analyze", name: "analyze", component: () => import("@/views/AnalyzeView.vue") },
  { path: "/stock/:ticker", name: "stock-detail", component: () => import("@/views/StockDetailView.vue"), props: true },
];

export default createRouter({ history: createWebHistory(), routes });
