/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite configuration for the React + TypeScript frontend. The dev server runs
// on port 5173 and communicates with the backend over HTTP/JSON.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    // Vitest owns the unit/integration tests under src/. The Playwright E2E
    // specs live in e2e/ and must not be collected by Vitest (Stage 3).
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["e2e/**", "node_modules/**", "dist/**"],
    coverage: {
      provider: "v8",
      // LCOV for later quality analysis (Stage 3 Requirement 6.2); text for a
      // quick console summary. The E2E specs live outside src and are not unit
      // coverage targets.
      reporter: ["text", "lcov"],
      reportsDirectory: "./coverage",
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/**/*.test.{ts,tsx}", "src/test/**", "src/vite-env.d.ts"],
    },
  },
});
