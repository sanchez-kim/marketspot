/// <reference types="node" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// 로컬 개발: /api 호출을 FastAPI(8000)로 프록시
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
