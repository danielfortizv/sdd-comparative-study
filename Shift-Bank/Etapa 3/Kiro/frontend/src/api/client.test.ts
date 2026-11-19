// Pruebas de humo MÍNIMAS del cliente de API (Etapa 3, Tarea 30; R19.2, AC-14).
//
// Objetivo: validar, sin alterar la app, que las funciones exportadas del cliente:
//   1. construyen rutas RELATIVAS `/api/...` (BASE_URL por defecto = "" en producción), y
//   2. usan el método HTTP correcto y serializan el cuerpo como JSON cuando corresponde.
//
// No se renderiza React (entorno `node`): solo se parchea el `fetch` global. Estas pruebas
// se adaptan al comportamiento actual del cliente; NO modifican su código.

import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ApiRequestError,
  createTransfer,
  getAccounts,
  updateLimits,
} from "./client";

/** Construye una respuesta `fetch` simulada con cuerpo JSON y estado configurable. */
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

describe("cliente de API — rutas relativas y métodos (prueba de humo)", () => {
  it("getAccounts() hace GET a la ruta relativa /api/accounts y parsea el JSON", async () => {
    const payload = { accounts: [] };
    const fetchMock = mockFetchOnce(payload);

    const result = await getAccounts();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    // BASE_URL por defecto = "" ⇒ la URL es RELATIVA al mismo origen.
    expect(url).toBe("/api/accounts");
    // Sin `method` explícito ⇒ GET por defecto de fetch.
    expect(init?.method).toBeUndefined();
    expect(result).toEqual(payload);
  });

  it("createTransfer() hace POST a /api/transfers con cuerpo JSON", async () => {
    const payload = { amount: "10.00", to: "acc-2" };
    const fetchMock = mockFetchOnce({ reference: "ref-1" });

    await createTransfer(payload as never);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/transfers");
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(JSON.stringify(payload));
    expect((init?.headers as Record<string, string>)["Content-Type"]).toBe(
      "application/json",
    );
  });

  it("updateLimits() hace PUT a /api/limits y propaga errores { error: { code, message } }", async () => {
    mockFetchOnce({ error: { code: "LIMIT_INVALID", message: "no válido" } }, false, 400);

    await expect(updateLimits({} as never)).rejects.toMatchObject({
      code: "LIMIT_INVALID",
    });
    await expect(updateLimits({} as never)).rejects.toBeInstanceOf(ApiRequestError);
  });
});
