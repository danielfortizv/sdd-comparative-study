/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite configuration for a React + TypeScript app, with Vitest test settings.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
    // Include every test under src so the registered coverage layout applies.
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      reportsDirectory: "./coverage",
      // Measure every executable production module under src. Do NOT exclude
      // production files. main.tsx is an executable production bootstrap and
      // stays in the denominator (Req 18.12/18.13); only genuine non-production
      // glue - tests, the test setup, and declaration-only env types - is
      // excluded (Req 18.14).
      include: ["src/**/*.ts", "src/**/*.tsx"],
      exclude: [
        "src/**/*.test.ts",
        "src/**/*.test.tsx",
        "src/test-setup.ts",
        "src/vite-env.d.ts",
      ],
    },
  },
});
