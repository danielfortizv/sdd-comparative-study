// Pruebas de humo del cliente v2 (Etapa 4): rutas relativas, headers de comando
// (Idempotency-Key UUID, Expected-Version) y propagación de errores { error: { code, message } }.

import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ApiV2Error,
  createConversion,
  createInternalTransferV2,
  getAccountsV2,
  newIdempotencyKey,
} from "./apiV2";

function mockFetchOnce(body: unknown, ok = true, status = 200) {
  const text = JSON.stringify(body);
  const fetchMock = vi.fn().mockResolvedValue({
    ok,
    status,
    text: () => Promise.resolve(text),
  } as unknown as Response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

describe("cliente v2 de la Etapa 4", () => {
  it("newIdempotencyKey() produce un UUID v4", () => {
    expect(newIdempotencyKey()).toMatch(UUID_RE);
  });

  it("getAccountsV2() hace GET a /api/v2/accounts", async () => {
    const fetchMock = mockFetchOnce({ accounts: [] });
    await getAccountsV2();
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v2/accounts");
    expect(init?.method).toBeUndefined();
  });

  it("createConversion() hace POST a /api/conversions con Idempotency-Key UUID", async () => {
    const fetchMock = mockFetchOnce({ status: "COMPLETED", rate: "9/10" });
    await createConversion({ from: "CHK-1001", to: "EUR-3001", amount: "100.00" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/conversions");
    expect(init?.method).toBe("POST");
    const headers = init?.headers as Record<string, string>;
    expect(headers["Idempotency-Key"]).toMatch(UUID_RE);
    expect(headers["Content-Type"]).toBe("application/json");
  });

  it("createInternalTransferV2() envía Expected-Version cuando se provee", async () => {
    const fetchMock = mockFetchOnce({ status: "COMPLETED" });
    await createInternalTransferV2(
      { from: "CHK-1001", to: "SAV-2001", amount: "10.00" },
      { "CHK-1001": 1, "SAV-2001": 1 },
    );
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v2/transfers");
    const headers = init?.headers as Record<string, string>;
    expect(JSON.parse(headers["Expected-Version"])).toEqual({ "CHK-1001": 1, "SAV-2001": 1 });
  });

  it("propaga errores { error: { code, message } } como ApiV2Error con status", async () => {
    mockFetchOnce({ error: { code: "IDEMPOTENCY_CONFLICT", message: "x" } }, false, 409);
    await expect(
      createConversion({ from: "A", to: "B", amount: "1.00" }),
    ).rejects.toMatchObject({ code: "IDEMPOTENCY_CONFLICT", status: 409 });
    mockFetchOnce({ error: { code: "ACCOUNT_VERSION_CONFLICT", message: "y" } }, false, 409);
    await expect(
      createInternalTransferV2({ from: "A", to: "B", amount: "1.00" }),
    ).rejects.toBeInstanceOf(ApiV2Error);
  });
});
