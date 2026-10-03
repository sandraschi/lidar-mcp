import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";

// Backend (FastAPI) on 11228, frontend dev on 11227. All /api traffic and
// the auto-docs are proxied so the SPA never hardcodes a backend origin.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 11227,
    proxy: {
      "/api": { target: "http://127.0.0.1:11228", changeOrigin: true },
      "/docs": { target: "http://127.0.0.1:11228", changeOrigin: true },
      "/openapi.json": { target: "http://127.0.0.1:11228", changeOrigin: true },
      "/redoc": { target: "http://127.0.0.1:11228", changeOrigin: true },
    },
  },
  preview: { port: 11227 },
});
