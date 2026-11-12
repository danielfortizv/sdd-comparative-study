// Playwright E2E configuration (Stage 3, design: E2E suite).
//
// Boots the REAL stack and drives a real Chromium browser against it with no
// API mocking (Requirements 1.1, 2.1):
//   - the real backend via `uvicorn` from ../backend, serving on port 8000
//     (the frontend's fixed API base URL), and
//   - the real frontend production build served by `vite preview` on port 4173.
//
// The in-process backend store is non-persistent, so a fresh `uvicorn` start
// gives a clean baseline; tests additionally use unique account/product data so
// they are independent. If either server fails to boot, Playwright fails the
// run (Requirement 1.3) rather than testing against a dead stack.

import { existsSync } from "node:fs";
import { defineConfig, devices } from "@playwright/test";

const FRONTEND_PORT = 4173;
const BACKEND_PORT = 8000;

/**
 * Resolve the uvicorn launch command for the real backend. Prefers the backend
 * virtualenv interpreter (`backend/.venv`) created per the README so the pinned
 * dependencies are used; falls back to `python` on PATH otherwise. Override
 * entirely with the BACKEND_CMD environment variable when needed (e.g. CI).
 */
function backendCommand(): string {
  const args = `-m uvicorn app.main:app --host 127.0.0.1 --port ${BACKEND_PORT}`;
  const venvWin = "../backend/.venv/Scripts/python.exe";
  const venvNix = "../backend/.venv/bin/python";
  if (existsSync(venvWin)) return `"${venvWin}" ${args}`;
  if (existsSync(venvNix)) return `"${venvNix}" ${args}`;
  return `python ${args}`;
}

export default defineConfig({
  testDir: "./e2e",
  // Serial execution keeps the single shared in-process backend session
  // deterministic across specs (one active session at a time).
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  timeout: 60_000,
  expect: { timeout: 10_000 },

  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: "on-first-retry",
    video: "retain-on-failure",
  },

  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],

  webServer: [
    {
      // Real backend. Uses the backend virtualenv interpreter when present
      // (created per the README), falling back to `python` on PATH. The
      // in-process store is non-persistent, so this boot is a clean baseline.
      command: process.env.BACKEND_CMD ?? backendCommand(),
      cwd: "../backend",
      url: `http://127.0.0.1:${BACKEND_PORT}/health`,
      // Always boot a fresh backend so the current code and a clean in-process
      // store are used (avoids reusing a stale server from a previous run).
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      // Real frontend production build served statically by Vite preview.
      command: `npm run build && npm run preview -- --port ${FRONTEND_PORT} --strictPort`,
      cwd: ".",
      url: `http://localhost:${FRONTEND_PORT}`,
      // Always rebuild + reserve the port so the latest production build is
      // what the browser loads.
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
    },
  ],
});
