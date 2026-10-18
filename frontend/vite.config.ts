import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// In development the browser talks to Vite, and Vite forwards /api to a backend: the mock API by default,
// or the real Spring Boot service with  VITE_API_TARGET=http://localhost:8080 npm run dev
const api = { "/api": { target: process.env.VITE_API_TARGET ?? "http://localhost:8787", changeOrigin: true } };

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: api },
  preview: { port: 4173, proxy: api },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
