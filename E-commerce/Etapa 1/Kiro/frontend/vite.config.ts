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
  },
});
