// Cliente de API. Envía y recibe montos como `string` (decimal-string, nunca `number`).
// Normaliza los errores { error: { code, message } } a una excepción con code/message.

import type {
  AccountsResponse,
  AchMfaResponse,
  BeneficiariesResponse,
  CreateAchRequest,
  CreateAchResponse,
  CreateBeneficiaryRequest,
  CreateBeneficiaryResponse,
  CreateRecurringRequest,
  CreateRecurringResponse,
  CreateTransferRequest,
  CreateTransferResponse,
  DeleteBeneficiaryResponse,
  LimitsResponse,
  MfaResponse,
  RecurringLifecycleResponse,
  RecurringResponse,
  TransfersHistoryResponse,
  UpdateLimitsRequest,
  UpdateLimitsResponse,
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

// ---------------------------------------------------------------------------
// Beneficiarios (Requisitos 1, 2)
// ---------------------------------------------------------------------------

export function getBeneficiaries(): Promise<BeneficiariesResponse> {
  return request<BeneficiariesResponse>("/api/beneficiaries");
}

export function createBeneficiary(
  payload: CreateBeneficiaryRequest
): Promise<CreateBeneficiaryResponse> {
  return request<CreateBeneficiaryResponse>("/api/beneficiaries", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteBeneficiary(id: string): Promise<DeleteBeneficiaryResponse> {
  return request<DeleteBeneficiaryResponse>(`/api/beneficiaries/${id}`, {
    method: "DELETE",
  });
}

// ---------------------------------------------------------------------------
// Transferencias ACH (Requisitos 3, 4, 5)
// ---------------------------------------------------------------------------

export function createAch(payload: CreateAchRequest): Promise<CreateAchResponse> {
  return request<CreateAchResponse>("/api/ach", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function confirmAchMfa(reference: string, code: string): Promise<AchMfaResponse> {
  return request<AchMfaResponse>(`/api/ach/${reference}/mfa`, {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

// ---------------------------------------------------------------------------
// Pagos recurrentes (Requisitos 8, 9, 12)
// ---------------------------------------------------------------------------

export function getRecurring(): Promise<RecurringResponse> {
  return request<RecurringResponse>("/api/recurring");
}

export function createRecurring(
  payload: CreateRecurringRequest
): Promise<CreateRecurringResponse> {
  return request<CreateRecurringResponse>("/api/recurring", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function pauseRecurring(id: string): Promise<RecurringLifecycleResponse> {
  return request<RecurringLifecycleResponse>(`/api/recurring/${id}/pause`, {
    method: "POST",
  });
}

export function resumeRecurring(id: string): Promise<RecurringLifecycleResponse> {
  return request<RecurringLifecycleResponse>(`/api/recurring/${id}/resume`, {
    method: "POST",
  });
}

export function cancelRecurring(id: string): Promise<RecurringLifecycleResponse> {
  return request<RecurringLifecycleResponse>(`/api/recurring/${id}/cancel`, {
    method: "POST",
  });
}

// ---------------------------------------------------------------------------
// Límites de transferencia dinámicos (Requisitos 13, 14)
// ---------------------------------------------------------------------------

export function getLimits(): Promise<LimitsResponse> {
  return request<LimitsResponse>("/api/limits");
}

export function updateLimits(
  payload: UpdateLimitsRequest
): Promise<UpdateLimitsResponse> {
  return request<UpdateLimitsResponse>("/api/limits", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
