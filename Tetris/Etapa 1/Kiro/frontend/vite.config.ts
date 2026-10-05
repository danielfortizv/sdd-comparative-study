import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Standard Vite configuration for a React + TypeScript app.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
