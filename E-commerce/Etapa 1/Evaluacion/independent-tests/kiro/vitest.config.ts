import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";
const productionRoot = fileURLToPath(
  new URL("../../../Kiro/frontend/src", import.meta.url),
);
const productionGlobRoot = productionRoot.split("\\").join("/");

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@kiro": productionRoot,
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["./frontend*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary", "lcov"],
      reportsDirectory: "./coverage-frontend",
      all: true,
      allowExternal: true,
      include: [`${productionGlobRoot}/**/*.{ts,tsx}`],
      exclude: [
        `${productionGlobRoot}/**/*.test.{ts,tsx}`,
        `${productionGlobRoot}/test/**`,
        `${productionGlobRoot}/main.tsx`,
        `${productionGlobRoot}/vite-env.d.ts`
      ],
    },
  },
});
