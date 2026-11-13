// Playwright E2E configuration (Stage 4).
//
// Boots the REAL distributed stack and drives a real Chromium browser against
// it with no API mocking:
//   - the four backend services (identity, commerce, reviews, gateway) started
//     by a global setup against the real RabbitMQ broker, and
//   - the real frontend production build served by `vite preview`, built with
//     its API base URL pointed at the gateway.
//
// The authoritative real-broker, multi-process acceptance suite is the pytest
// suite in `tests_e2e/` (purchase, review lifecycle, access denial, duplicate
// delivery, outage/recovery). These Playwright specs additionally verify the
// unchanged UI journeys against the gateway.
//
// Requires the Stage 4 services venv (scripts/setup.ps1) and a running broker.

import { defineConfig, devices } from "@playwright/test";

const FRONTEND_PORT = Number(process.env.FRONTEND_PORT ?? 18300);
const GATEWAY_PORT = Number(process.env.GATEWAY_PORT ?? 18200);
const GATEWAY_URL = `http://localhost:${GATEWAY_PORT}`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  timeout: 90_000,
  expect: { timeout: 15_000 },

  // Starts/stops the four Stage 4 services + broker check before/after the run.
  globalSetup: "./e2e/global-setup.ts",
  globalTeardown: "./e2e/global-teardown.ts",

  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: "on-first-retry",
    video: "retain-on-failure",
  },

  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],

  webServer: [
    {
      // Real frontend production build, API base URL pointed at the gateway.
      command: `npm run build && npm run preview -- --port ${FRONTEND_PORT} --strictPort`,
      cwd: ".",
      url: `http://localhost:${FRONTEND_PORT}`,
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
      env: { VITE_API_BASE_URL: GATEWAY_URL },
    },
  ],
});
