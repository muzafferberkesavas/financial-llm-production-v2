import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", redirect: "/overview" },
  { path: "/overview", name: "overview", component: () => import("@/views/OverviewView.vue") },
  { path: "/signals", name: "signals", component: () => import("@/views/SignalsView.vue") },
  { path: "/portfolio", name: "portfolio", component: () => import("@/views/PortfolioView.vue") },
];

export default createRouter({ history: createWebHistory(), routes });
