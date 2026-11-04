import {
  Account,
  TransferRequest,
  TransferResponse,
  Transaction,
  MfaStatus,
  MfaVerifyResponse,
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
  getAccounts: (): Promise<Account[]> => request<Account[]>('/accounts'),

  getAccount: (id: number): Promise<Account> => request<Account>(`/accounts/${id}`),

  getTransactions: (accountId?: number): Promise<Transaction[]> => {
    const query = accountId !== undefined ? `?account_id=${accountId}` : '';
    return request<Transaction[]>(`/transactions${query}`);
  },

  executeTransfer: (payload: TransferRequest): Promise<TransferResponse> =>
    request<TransferResponse>('/transfers', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getMfaStatus: (): Promise<MfaStatus> => request<MfaStatus>('/mfa/status'),

  verifyMfa: (pin: string): Promise<MfaVerifyResponse> =>
    request<MfaVerifyResponse>('/mfa/verify', {
      method: 'POST',
      body: JSON.stringify({ pin }),
    }),
};
