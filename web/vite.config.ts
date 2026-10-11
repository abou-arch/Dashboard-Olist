import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// En développement, les appels /api sont relayés vers l'API FastAPI (port 8000).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": "http://localhost:8000" },
  },
  build: {
    chunkSizeWarningLimit: 900,
  },
});
