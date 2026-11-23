// Playwright global teardown (Stage 4): stop the backend services started by
// global-setup, identified by their recorded process ids.

import { existsSync, readFileSync, rmSync } from "node:fs";
import { join } from "node:path";

const PID_FILE = join("e2e", ".stage4-e2e-pids.json");

export default async function globalTeardown() {
  if (!existsSync(PID_FILE)) return;
  const pids: number[] = JSON.parse(readFileSync(PID_FILE, "utf-8"));
  for (const pid of pids) {
    try {
      process.kill(pid);
    } catch {
      /* already gone */
    }
  }
  rmSync(PID_FILE, { force: true });
}
