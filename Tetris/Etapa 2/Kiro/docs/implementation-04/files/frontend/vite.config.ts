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
      // Measure every production module under src. Do NOT exclude production
      // files. Only non-production glue (entry, test setup, tests, env types)
      // is excluded so the gate reflects real production coverage.
      include: ["src/**/*.ts", "src/**/*.tsx"],
      exclude: [
        "src/**/*.test.ts",
        "src/**/*.test.tsx",
        "src/test-setup.ts",
        "src/main.tsx",
        "src/vite-env.d.ts",
      ],
    },
  },
});
