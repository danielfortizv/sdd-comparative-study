// Cliente de API de la Etapa 4 (multidivisa): cuentas v2, conversiones y transferencias internas
// con headers de comando `Idempotency-Key` (UUID) y `Expected-Version` (D-13/D-14). Montos como
// `string` (decimal-string), nunca `number`.

import type { Currency } from "./currencyFormat";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export interface AccountV2 {
  public_id: string;
  name: string;
  currency: Currency;
  balance: string; // decimal-string
  version: number;
}

export interface AccountsV2Response {
  accounts: AccountV2[];
}

export interface ConversionResponse {
  status: string;
  rate: string; // "9/10"
  from: { public_id: string; currency: Currency; amount: string };
  to: { public_id: string; currency: Currency; amount: string };
  event_ids: string[];
}

export class ApiV2Error extends Error {
  code: string;
  status: number;
  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
    this.name = "ApiV2Error";
  }
}

/**
 * Genera un UUID v4 criptográficamente seguro para `Idempotency-Key`.
 *
 * Seguridad (T29, SonarQube typescript:S2245): NUNCA se usa `Math.random()` para identificadores
 * sensibles de idempotencia. Se prefiere `crypto.randomUUID()`; si no existe (navegador antiguo),
 * se compone un UUID v4 con bytes de `crypto.getRandomValues()` (CSPRNG). Si no hay aleatoriedad
 * segura disponible, se FALLA de forma segura (lanza) en lugar de degradar a un PRNG inseguro.
 */
export function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    // UUID v4: fijar versión (byte 6) y variante (byte 8) por RFC 4122.
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex: string[] = [];
    for (let i = 0; i < 256; i++) hex.push((i + 0x100).toString(16).slice(1));
    const b = Array.from(bytes, (v) => hex[v]);
    return (
      b[0] + b[1] + b[2] + b[3] + "-" + b[4] + b[5] + "-" + b[6] + b[7] + "-" +
      b[8] + b[9] + "-" + b[10] + b[11] + b[12] + b[13] + b[14] + b[15]
    );
  }
  // Sin CSPRNG disponible: fallar de forma segura (no degradar a Math.random, S2245).
  throw new Error(
    "No hay una fuente de aleatoriedad criptográficamente segura disponible para generar " +
      "Idempotency-Key; se aborta en lugar de usar un generador inseguro.",
  );
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);
  const text = await res.text();
  const body = text ? JSON.parse(text) : {};
  if (!res.ok) {
    const err = body?.error ?? { code: "UNKNOWN", message: "Error" };
    throw new ApiV2Error(err.code, err.message, res.status);
  }
  return body as T;
}

export function getAccountsV2(): Promise<AccountsV2Response> {
  return request<AccountsV2Response>("/api/v2/accounts");
}

function commandHeaders(expectedVersion?: Record<string, number>): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Idempotency-Key": newIdempotencyKey(),
  };
  if (expectedVersion) headers["Expected-Version"] = JSON.stringify(expectedVersion);
  return headers;
}

export function createConversion(
  payload: { from: string; to: string; amount: string },
  expectedVersion?: Record<string, number>,
): Promise<ConversionResponse> {
  return request<ConversionResponse>("/api/conversions", {
    method: "POST",
    headers: commandHeaders(expectedVersion),
    body: JSON.stringify(payload),
  });
}

export function createInternalTransferV2(
  payload: { from: string; to: string; amount: string },
  expectedVersion?: Record<string, number>,
): Promise<ConversionResponse> {
  return request<ConversionResponse>("/api/v2/transfers", {
    method: "POST",
    headers: commandHeaders(expectedVersion),
    body: JSON.stringify(payload),
  });
}
