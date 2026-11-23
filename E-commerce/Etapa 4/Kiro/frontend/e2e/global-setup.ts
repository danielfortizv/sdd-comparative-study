// Playwright global setup (Stage 4): boot the four backend services against the
// real RabbitMQ broker before the browser specs run. Each service gets its own
// temp SQLite store and a per-run event namespace so broker state is isolated.
//
// Process ids are written to e2e/.stage4-e2e-pids.json for the teardown to stop.

import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const ROOT = join(process.cwd(), "..");
const SERVICES = join(ROOT, "services");
const VENV_PY_WIN = join(SERVICES, ".venv", "Scripts", "python.exe");
const VENV_PY_NIX = join(SERVICES, ".venv", "bin", "python");
const PY = existsSync(VENV_PY_WIN)
  ? VENV_PY_WIN
  : existsSync(VENV_PY_NIX)
    ? VENV_PY_NIX
    : "python";

const GATEWAY_PORT = Number(process.env.GATEWAY_PORT ?? 18200);
const IDENTITY_PORT = Number(process.env.IDENTITY_PORT ?? 18201);
const COMMERCE_PORT = Number(process.env.COMMERCE_PORT ?? 18202);
const REVIEWS_PORT = Number(process.env.REVIEWS_PORT ?? 18203);
const AMQP_URL =
  process.env.AMQP_URL ??
  "amqp://ecommerce:stage4-demo@127.0.0.1:5672/stage4_kiro";

const PID_FILE = join("e2e", ".stage4-e2e-pids.json");

async function waitHealth(port: number, timeoutMs = 45000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const resp = await fetch(`http://127.0.0.1:${port}/health`);
      if (resp.ok) return;
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`Stage 4 service on port ${port} did not become healthy`);
}

export default async function globalSetup() {
  const tmp = mkdtempSync(join(tmpdir(), "stage4-pw-"));
  const namespace = `stage4.kiro.pw.${Date.now()}`;
  const env = {
    ...process.env,
    AMQP_URL,
    EVENT_NAMESPACE: namespace,
    IDENTITY_PORT: String(IDENTITY_PORT),
    COMMERCE_PORT: String(COMMERCE_PORT),
    REVIEWS_PORT: String(REVIEWS_PORT),
    GATEWAY_PORT: String(GATEWAY_PORT),
    IDENTITY_URL: `http://127.0.0.1:${IDENTITY_PORT}`,
    COMMERCE_URL: `http://127.0.0.1:${COMMERCE_PORT}`,
    REVIEWS_URL: `http://127.0.0.1:${REVIEWS_PORT}`,
    IDENTITY_DB_PATH: join(tmp, "identity.db"),
    COMMERCE_DB_PATH: join(tmp, "commerce.db"),
    REVIEWS_DB_PATH: join(tmp, "reviews.db"),
    REVIEW_IMAGE_DIR: join(tmp, "images"),
    FRONTEND_PORT: String(process.env.FRONTEND_PORT ?? 18300),
  };

  const pids: number[] = [];
  const start = (name: string, port: number) => {
    const proc = spawn(
      PY,
      ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(port)],
      { cwd: join(SERVICES, name), env, stdio: "inherit" },
    );
    if (proc.pid) pids.push(proc.pid);
  };

  start("identity", IDENTITY_PORT);
  start("commerce", COMMERCE_PORT);
  start("reviews", REVIEWS_PORT);
  await waitHealth(IDENTITY_PORT);
  await waitHealth(COMMERCE_PORT);
  await waitHealth(REVIEWS_PORT);
  start("gateway", GATEWAY_PORT);
  await waitHealth(GATEWAY_PORT);

  writeFileSync(PID_FILE, JSON.stringify(pids));
}
