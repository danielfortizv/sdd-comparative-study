import {
  Account,
  TransferRequest,
  TransferResponse,
  ConversionRequest,
  ConversionResponse,
  Transaction,
  MfaStatus,
  MfaVerifyResponse,
  Beneficiary,
  BeneficiaryCreateRequest,
  AchTransferRequest,
  AchTransferResponse,
  RecurringSchedule,
  RecurringScheduleCreateRequest,
  TransferLimits,
  TransferLimitsUpdateRequest,
  PublicKeyResponse,
  EncryptedFieldPayload,
} from './types';
import { encryptField, invalidatePublicKeyCache } from './crypto';

const API_BASE = '/api';

export class ApiError extends Error {
  status: number;
  data: any;
  code: string;
  detail: any;

  constructor(status: number, message: string, data?: any, code?: string, detail?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
    this.code =
      code ||
      (data?.code
        ? String(data.code)
        : typeof data?.detail === 'object' && data?.detail?.code
        ? String(data.detail.code)
        : status === 409 && message.toLowerCase().includes('version')
        ? 'ACCOUNT_VERSION_CONFLICT'
        : status === 409 && message.toLowerCase().includes('idempotenc')
        ? 'IDEMPOTENCY_KEY_REUSE'
        : 'ERROR');
    this.detail = detail !== undefined ? detail : (data?.detail !== undefined ? data.detail : data);
  }
}

export function generateIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  let response: Response;
  try {
    response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });
  } catch (netErr: any) {
    throw new ApiError(
      0,
      netErr?.message ? `Network error: ${netErr.message}` : 'Network connection failure',
      null,
      'NETWORK_ERROR',
      null
    );
  }

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    let code = 'ERROR';
    let detail: any = null;
    let data: any = null;

    try {
      data = await response.json();
      if (data) {
        if (typeof data === 'string') {
          message = data;
        } else if (typeof data === 'object') {
          // Check top-level code and message
          if (typeof data.code === 'string') {
            code = data.code;
          }
          if (typeof data.message === 'string') {
            message = data.message;
          }

          // Check nested detail
          if (data.detail !== undefined) {
            detail = data.detail;
            if (typeof data.detail === 'string') {
              if (!data.message) {
                message = data.detail;
              }
            } else if (typeof data.detail === 'object' && data.detail !== null) {
              if (typeof data.detail.code === 'string') {
                code = data.detail.code;
              }
              if (typeof data.detail.message === 'string' && !data.message) {
                message = data.detail.message;
              }
            }
          } else {
            detail = data;
          }
        }
      }
    } catch {
      message = response.statusText || `Request failed with status ${response.status}`;
    }

    throw new ApiError(response.status, message, data, code, detail);
  }

  return response.json();
}

/**
 * Safely encrypt a sensitive banking coordinate into an EncryptedFieldPayload.
 * If encryption fails, immediately throws an ApiError without transmitting plaintext.
 */
async function secureField(
  val: string | EncryptedFieldPayload | undefined
): Promise<string | EncryptedFieldPayload | undefined> {
  if (val === undefined || val === null) {
    return undefined;
  }
  if (typeof val === 'object' && val.__encrypted__) {
    return val;
  }
  if (typeof val === 'string') {
    const trimmed = val.trim();
    if (!trimmed) {
      return val;
    }
    try {
      return await encryptField(trimmed);
    } catch (err: any) {
      throw new ApiError(
        0,
        'Client-side encryption failure: Unable to secure sensitive coordinates. Request aborted before transmission.',
        { originalError: err?.message || String(err) }
      );
    }
  }
  return val;
}

/**
 * Execute an API call that involves client-side encrypted fields with a bounded retry.
 * If the server returns HTTP 400 with KEY_EXPIRED or INVALID_KEY_ID (e.g. key expired or server restarted),
 * invalidates the public key cache and retries the operation once with a refreshed key.
 * Never retries with plaintext.
 */
async function withEncryptionRetry<T>(operation: () => Promise<T>): Promise<T> {
  try {
    return await operation();
  } catch (err: any) {
    if (
      err instanceof ApiError &&
      err.status === 400 &&
      (err.data?.detail === 'KEY_EXPIRED' || err.data?.detail === 'INVALID_KEY_ID')
    ) {
      invalidatePublicKeyCache();
      return await operation();
    }
    throw err;
  }
}

export const api = {
  // Accounts & Transactions
  getAccounts: (): Promise<Account[]> => request<Account[]>('/accounts'),

  getAccount: (id: number): Promise<Account> => request<Account>(`/accounts/${id}`),

  getTransactions: (accountId?: number): Promise<Transaction[]> => {
    const query = accountId !== undefined ? `?account_id=${accountId}` : '';
    return request<Transaction[]>(`/transactions${query}`);
  },

  // Internal Transfers
  executeTransfer: (payload: TransferRequest, idempotencyKey?: string): Promise<TransferResponse> =>
    request<TransferResponse>('/transfers', {
      method: 'POST',
      headers: {
        'Idempotency-Key': idempotencyKey || generateIdempotencyKey(),
      },
      body: JSON.stringify(payload),
    }),

  // Currency Conversions
  executeConversion: (payload: ConversionRequest, idempotencyKey?: string): Promise<ConversionResponse> =>
    request<ConversionResponse>('/conversions', {
      method: 'POST',
      headers: {
        'Idempotency-Key': idempotencyKey || generateIdempotencyKey(),
      },
      body: JSON.stringify(payload),
    }),

  // MFA
  getMfaStatus: (): Promise<MfaStatus> => request<MfaStatus>('/mfa/status'),

  verifyMfa: (pin: string): Promise<MfaVerifyResponse> =>
    request<MfaVerifyResponse>('/mfa/verify', {
      method: 'POST',
      body: JSON.stringify({ pin }),
    }),

  // Stage 2: Beneficiaries
  getBeneficiaries: (): Promise<Beneficiary[]> => request<Beneficiary[]>('/beneficiaries'),

  createBeneficiary: (payload: BeneficiaryCreateRequest): Promise<Beneficiary> =>
    withEncryptionRetry(async () => {
      const routing = await secureField(payload.routing_number);
      const account = await secureField(payload.account_number);
      return request<Beneficiary>('/beneficiaries', {
        method: 'POST',
        body: JSON.stringify({ ...payload, routing_number: routing, account_number: account }),
      });
    }),

  deleteBeneficiary: (id: number): Promise<{ status: string; id: number }> =>
    request<{ status: string; id: number }>(`/beneficiaries/${id}`, {
      method: 'DELETE',
    }),

  // Stage 2: ACH Transfers
  executeAchTransfer: (payload: AchTransferRequest, idempotencyKey?: string): Promise<AchTransferResponse> =>
    withEncryptionRetry(async () => {
      const routing = await secureField(payload.routing_number);
      const account = await secureField(payload.account_number);
      return request<AchTransferResponse>('/transfers/ach', {
        method: 'POST',
        headers: {
          'Idempotency-Key': idempotencyKey || generateIdempotencyKey(),
        },
        body: JSON.stringify({ ...payload, routing_number: routing, account_number: account }),
      });
    }),

  // Stage 2: Recurring Schedules
  getRecurringSchedules: (): Promise<RecurringSchedule[]> => request<RecurringSchedule[]>('/recurring'),

  createRecurringSchedule: (payload: RecurringScheduleCreateRequest): Promise<RecurringSchedule> =>
    withEncryptionRetry(async () => {
      const routing = await secureField(payload.routing_number);
      const account = await secureField(payload.account_number);
      return request<RecurringSchedule>('/recurring', {
        method: 'POST',
        body: JSON.stringify({ ...payload, routing_number: routing, account_number: account }),
      });
    }),

  pauseRecurringSchedule: (id: number): Promise<RecurringSchedule> =>
    request<RecurringSchedule>(`/recurring/${id}/pause`, {
      method: 'POST',
    }),

  resumeRecurringSchedule: (id: number): Promise<RecurringSchedule> =>
    request<RecurringSchedule>(`/recurring/${id}/resume`, {
      method: 'POST',
    }),

  cancelRecurringSchedule: (id: number): Promise<RecurringSchedule> =>
    request<RecurringSchedule>(`/recurring/${id}/cancel`, {
      method: 'POST',
    }),

  // Stage 3: Cryptography
  getPublicKey: (): Promise<PublicKeyResponse> => request<PublicKeyResponse>('/crypto/public-key'),

  // Stage 2: Transfer Limits
  getLimits: (): Promise<TransferLimits> => request<TransferLimits>('/limits'),

  updateLimits: (payload: TransferLimitsUpdateRequest): Promise<TransferLimits> =>
    request<TransferLimits>('/limits', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
};
