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
} from './types';

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
    request<Beneficiary>('/beneficiaries', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  deleteBeneficiary: (id: number): Promise<{ status: string; id: number }> =>
    request<{ status: string; id: number }>(`/beneficiaries/${id}`, {
      method: 'DELETE',
    }),

  // Stage 2: ACH Transfers
  executeAchTransfer: (payload: AchTransferRequest): Promise<AchTransferResponse> =>
    request<AchTransferResponse>('/transfers/ach', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Stage 2: Recurring Schedules
  getRecurringSchedules: (): Promise<RecurringSchedule[]> => request<RecurringSchedule[]>('/recurring'),

  createRecurringSchedule: (payload: RecurringScheduleCreateRequest): Promise<RecurringSchedule> =>
    request<RecurringSchedule>('/recurring', {
      method: 'POST',
      body: JSON.stringify(payload),
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

  // Stage 2: Transfer Limits
  getLimits: (): Promise<TransferLimits> => request<TransferLimits>('/limits'),

  updateLimits: (payload: TransferLimitsUpdateRequest): Promise<TransferLimits> =>
    request<TransferLimits>('/limits', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
};
