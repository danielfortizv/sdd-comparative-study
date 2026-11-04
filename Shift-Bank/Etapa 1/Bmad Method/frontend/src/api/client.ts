import { Account } from '../types/account';

export const DEFAULT_CUSTOMER_ID = 'cust_mock_001';

export class ApiError extends Error {
  code: string;
  details?: unknown;

  constructor(code: string, message: string, details?: unknown) {
    super(message);
    this.code = code;
    this.details = details;
    this.name = 'ApiError';
  }
}

export interface TransferAccountSummary {
  id: string;
  balance_cents: number;
  balance_formatted: string;
}

export interface TransferItemData {
  id: string;
  source_account_id: string;
  destination_account_id: string;
  amount_cents: number;
  amount_formatted: string;
  status: string;
  created_at: string;
}

export interface TransferResponseData {
  transfer: TransferItemData;
  status: string;
  source_account?: TransferAccountSummary;
  destination_account?: TransferAccountSummary;
}

export function generateIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export async function fetchAccounts(customerId: string = DEFAULT_CUSTOMER_ID): Promise<Account[]> {
  const response = await fetch('/api/accounts', {
    headers: {
      'Content-Type': 'application/json',
      'X-Customer-Id': customerId,
    },
  });

  const data = await response.json();

  if (!response.ok) {
    const err = data?.error || {};
    throw new ApiError(
      err.code || 'UNKNOWN_ERROR',
      err.message || `HTTP ${response.status} Error`,
      err.details
    );
  }

  return data as Account[];
}

export async function initiateTransfer(
  fromAccountId: string,
  toAccountId: string,
  amountCents: number,
  idempotencyKey?: string,
  customerId: string = DEFAULT_CUSTOMER_ID
): Promise<TransferResponseData> {
  const key = idempotencyKey || generateIdempotencyKey();
  const response = await fetch('/api/transfers', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Customer-Id': customerId,
      'Idempotency-Key': key,
    },
    body: JSON.stringify({
      from_account_id: fromAccountId,
      to_account_id: toAccountId,
      amount_cents: amountCents,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    const err = data?.error || {};
    throw new ApiError(
      err.code || 'TRANSFER_FAILED',
      err.message || `HTTP ${response.status} Error`,
      err.details
    );
  }

  return data as TransferResponseData;
}
