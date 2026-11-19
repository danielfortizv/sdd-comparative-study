/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  // Configuración MÍNIMA de Vitest solo-dev (Etapa 3, Tarea 30). No afecta al build de
  // producción (`tsc && vite build`): Vite ignora el bloque `test` fuera de Vitest.
  // Entorno `node` porque la prueba de humo del cliente de API no renderiza React
  // (solo parchea `fetch` global). Esto NO altera la app ni añade deps de runtime.
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
    // Cobertura MÍNIMA solo-dev para el PRE/FINAL de SonarQube (Etapa 3, Tarea 31).
    // Produce frontend/coverage/lcov.info (importado por el escáner). Provider v8 vía
    // @vitest/coverage-v8 (devDependency); no altera la app ni el build de producción.
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      reportsDirectory: "coverage",
    },
  },
});
