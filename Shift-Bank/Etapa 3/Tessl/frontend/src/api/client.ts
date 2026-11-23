import {
  Account,
  TransferRequest,
  TransferResponse,
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

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    let data = null;
    try {
      data = await response.json();
      if (data?.detail) {
        errorDetail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // fallback to status text
    }
    throw new ApiError(response.status, errorDetail, data);
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
      // Bounded retry: attempt exactly once with fresh key
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
  executeTransfer: (payload: TransferRequest): Promise<TransferResponse> =>
    request<TransferResponse>('/transfers', {
      method: 'POST',
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
  executeAchTransfer: (payload: AchTransferRequest): Promise<AchTransferResponse> =>
    withEncryptionRetry(async () => {
      const routing = await secureField(payload.routing_number);
      const account = await secureField(payload.account_number);
      return request<AchTransferResponse>('/transfers/ach', {
        method: 'POST',
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
