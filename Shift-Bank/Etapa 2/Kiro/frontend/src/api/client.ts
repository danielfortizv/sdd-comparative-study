// Cliente de API. Envía y recibe montos como `string` (decimal-string, nunca `number`).
// Normaliza los errores { error: { code, message } } a una excepción con code/message.

import type {
  AccountsResponse,
  CreateTransferRequest,
  CreateTransferResponse,
  MfaResponse,
  TransfersHistoryResponse,
} from "../types";

const BASE_URL = "http://localhost:8000";

export class ApiRequestError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "ApiRequestError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const err = data?.error;
    if (err && typeof err.code === "string") {
      throw new ApiRequestError(err.code, err.message ?? "Error");
    }
    throw new ApiRequestError("UNKNOWN", `Error HTTP ${response.status}`);
  }

  return data as T;
}

export function getAccounts(): Promise<AccountsResponse> {
  return request<AccountsResponse>("/api/accounts");
}

export function createTransfer(
  payload: CreateTransferRequest
): Promise<CreateTransferResponse> {
  return request<CreateTransferResponse>("/api/transfers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function confirmMfa(reference: string, code: string): Promise<MfaResponse> {
  return request<MfaResponse>(`/api/transfers/${reference}/mfa`, {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

export function getHistory(): Promise<TransfersHistoryResponse> {
  return request<TransfersHistoryResponse>("/api/transfers");
}
