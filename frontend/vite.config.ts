import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  // Relative base so the same static build works at the domain root
  // (Vercel, nginx, Caddy) AND under a sub-path (GitHub Pages project
  // site: /school-ms/). With an absolute "/" base, Pages 404s every
  // asset and the page renders blank.
  base: "./",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  build: { outDir: "dist" },
});
