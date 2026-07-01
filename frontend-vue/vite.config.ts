import { defineConfig } from "vite";
import { fileURLToPath, URL } from "node:url";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";

// Dev proxy: /api/* → backend panel_server (VITE_API_URL, default :8000).
const API = process.env.VITE_API_URL ?? "http://localhost:8000";

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    proxy: {
      "/api": { target: API, changeOrigin: true, rewrite: (p) => p.replace(/^\/api/, ""), timeout: 300000 },
    },
  },
});
