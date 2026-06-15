import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", redirect: "/signals" },
  { path: "/signals", name: "signals", component: () => import("@/views/SignalsView.vue") },
  { path: "/portfolio", name: "portfolio", component: () => import("@/views/PortfolioView.vue") },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});
