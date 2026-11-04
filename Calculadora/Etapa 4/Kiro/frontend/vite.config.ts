/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Frontend calls the backend at POST /api/v1/evaluate. The dev server proxies
// any /api request to the FastAPI backend so the client can use a relative path.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/tests/setup.ts',
    css: true,
    coverage: {
      provider: 'v8',
      // Measure all client source; exclude files that are not meaningful
      // coverage targets (tests, setup, type decls, and the DOM bootstrap).
      include: ['src/**'],
      exclude: [
        'src/tests/**',
        '**/*.test.ts',
        '**/*.test.tsx',
        'src/vite-env.d.ts',
        'src/main.tsx',
      ],
      // Fail the run (and report it) if coverage drops below the gate on any
      // of these metrics.
      thresholds: {
        statements: 80,
        branches: 80,
        functions: 80,
        lines: 80,
      },
    },
  },
});
