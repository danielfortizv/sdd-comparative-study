import {
  Account,
  Transfer,
  HistoryEntry,
  MFAConfirmResponse,
  LimitResponse,
  LimitUpdate,
  Beneficiary,
  BeneficiaryCreate,
  AchTransferCreate,
  AchTransferResponse,
  RecurringSchedule,
  RecurringScheduleCreate,
  ConversionResponse,
} from './types';
import { encryptPayload } from './crypto';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

/**
 * Defensive utility to extract a clear string error message from the backend API response payload.
 * Prevents [object Object] displaying when complex or structured errors are returned.
 */
function getErrorMessage(errData: any, defaultMsg: string): string {
  if (!errData || !errData.detail) return defaultMsg;
  if (typeof errData.detail === 'string') return errData.detail;
  if (Array.isArray(errData.detail)) {
    return errData.detail.map((err: any) => err.msg || JSON.stringify(err)).join(', ');
  }
  if (typeof errData.detail === 'object') {
    return errData.detail.detail || JSON.stringify(errData.detail);
  }
  return String(errData.detail);
}

export class BankApiError extends Error {
  constructor(message: string, readonly code: string | undefined, readonly status: number) {
    super(message);
    this.name = 'BankApiError';
  }
}

export function createIdempotencyKey(): string {
  return globalThis.crypto.randomUUID();
}

async function readApiError(res: Response, fallback: string): Promise<BankApiError> {
  const data = await res.json().catch(() => ({}));
  const detail = data?.detail;
  const code = typeof detail === 'object' ? detail.code : undefined;
  const message = typeof detail === 'object' ? detail.message : getErrorMessage(data, fallback);
  return new BankApiError(message || fallback, code, res.status);
}

async function encryptedPost<T>(path: string, payload: object, key: string): Promise<T> {
  const envelope = await encryptPayload(payload);
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Idempotency-Key': key },
    body: JSON.stringify(envelope),
  });
  if (!res.ok && res.status !== 202 && res.status !== 201) throw await readApiError(res, 'Bank request failed');
  return res.json();
}

/**
 * Fetches all mock accounts from the backend API.
 */
export async function fetchAccounts(): Promise<Account[]> {
  const res = await fetch(`${API_BASE_URL}/accounts`);
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(getErrorMessage(errData, 'Failed to fetch accounts'));
  }
  return res.json();
}

/**
 * Fetches the chronological transaction history for a specific account.
 */
export async function fetchHistory(accountId: string): Promise<HistoryEntry[]> {
  const res = await fetch(`${API_BASE_URL}/accounts/${accountId}/history`);
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(getErrorMessage(errData, 'Failed to fetch transaction history'));
  }
  return res.json();
}

/**
 * Initiates a standard or sensitive internal fund transfer.
 * Encrypts payload client-side into CryptographicEnvelope (FR-001, FR-002).
 * Can return 200 OK (Completed) or 202 Accepted (Pending MFA).
 */
export async function initiateTransfer(
  sourceAccountId: string,
  destinationAccountId: string,
  amount: string,
  expectedVersions: Record<string, number> = {},
  key = createIdempotencyKey(),
): Promise<Transfer> {
  return encryptedPost<Transfer>('/transfers', {
    source_account_id: sourceAccountId,
    destination_account_id: destinationAccountId,
    amount,
    expected_versions: expectedVersions,
  }, key);
}

/**
 * Submits the MFA verification code to finalize a sensitive internal or ACH transfer.
 * Encrypts MFA code into CryptographicEnvelope (FR-002, FR-008).
 */
export async function confirmMFA(
  transferId: string,
  code: string,
  expectedVersions: Record<string, number> = {},
  key = createIdempotencyKey(),
): Promise<MFAConfirmResponse> {
  return encryptedPost(`/transfers/${transferId}/confirm-mfa`, { code, expected_versions: expectedVersions }, key);
}

export async function convertFunds(payload: { source_account_id: string; destination_account_id: string; source_amount: string; expected_versions: Record<string, number> }, key: string): Promise<ConversionResponse> {
  return encryptedPost('/conversions', payload, key);
}

/**
 * Stage 2: Fetches active dynamic limits and daily consumption (LIM-01, LIM-02).
 */
export async function fetchLimits(): Promise<LimitResponse> {
  const res = await fetch(`${API_BASE_URL}/limits`);
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(getErrorMessage(errData, 'Failed to fetch transfer limits'));
  }
  return res.json();
}

/**
 * Stage 2: Updates user-configurable per-transfer and daily limits (LIM-02, D-01, D-07).
 * Encrypts update payload client-side into CryptographicEnvelope.
 */
export async function updateLimits(payload: LimitUpdate): Promise<LimitResponse> {
  const envelope = await encryptPayload(payload);

  const res = await fetch(`${API_BASE_URL}/limits`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(envelope),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(getErrorMessage(errData, 'Failed to update transfer limits'));
  }
  return res.json();
}

/**
 * Stage 2: Fetches all saved ACH beneficiaries (ACH-02).
 */
export async function fetchBeneficiaries(): Promise<Beneficiary[]> {
  const res = await fetch(`${API_BASE_URL}/beneficiaries`);
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(getErrorMessage(errData, 'Failed to fetch beneficiaries'));
  }
  return res.json();
}

/**
 * Stage 2: Creates and saves a new ACH beneficiary (ACH-01..03, D-08).
 * Encrypts beneficiary details into CryptographicEnvelope.
 */
export async function createBeneficiary(payload: BeneficiaryCreate): Promise<Beneficiary> {
  const envelope = await encryptPayload(payload);

  const res = await fetch(`${API_BASE_URL}/beneficiaries`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(envelope),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(getErrorMessage(errData, 'Failed to create beneficiary'));
  }
  return res.json();
}

/**
 * Stage 2: Deletes a saved ACH beneficiary while preserving past transaction snapshots (REC-11, D-08).
 */
export async function deleteBeneficiary(id: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/beneficiaries/${id}`, {
    method: 'DELETE',
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(getErrorMessage(errData, 'Failed to delete beneficiary'));
  }
}

/**
 * Stage 2: Initiates a simulated third-party ACH transfer (ACH-04..05).
 * Encrypts ACH transfer details into CryptographicEnvelope.
 * Can return 201 Created (Pending settlement) or 202 Accepted (Pending MFA).
 */
export async function initiateAchTransfer(payload: AchTransferCreate, key = createIdempotencyKey()): Promise<AchTransferResponse> {
  return encryptedPost('/transfers/ach', payload, key);
}

/**
 * Stage 2: Fetches all recurring payment schedules with automatic on-demand expiration sweep (REC-01..12, F-08).
 */
export async function fetchSchedules(): Promise<RecurringSchedule[]> {
  const res = await fetch(`${API_BASE_URL}/recurring-schedules`);
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(getErrorMessage(errData, 'Failed to fetch recurring schedules'));
  }
  return res.json();
}

/**
 * Stage 2: Creates a recurring schedule for internal or ACH transfers (REC-01..04).
 * Encrypts schedule instructions into CryptographicEnvelope.
 * Can return 201 Created (ACTIVE) or 202 Accepted (PENDING_MFA).
 */
export async function createSchedule(payload: RecurringScheduleCreate, key = createIdempotencyKey()): Promise<RecurringSchedule> {
  return encryptedPost('/recurring-schedules', payload, key);
}

/**
 * Stage 2: Confirms MFA code for a sensitive recurring schedule (D-03, D-05).
 * Encrypts MFA code into CryptographicEnvelope.
 */
export async function confirmScheduleMFA(scheduleId: string, code: string, expectedVersions: Record<string, number> = {}, key = createIdempotencyKey()): Promise<RecurringSchedule> {
  return encryptedPost(`/recurring-schedules/${scheduleId}/confirm-mfa`, { code, expected_versions: expectedVersions }, key);
}

/**
 * Stage 2: Pauses an ACTIVE recurring schedule (REC-06, A18).
 */
export async function pauseSchedule(scheduleId: string): Promise<RecurringSchedule> {
  const res = await fetch(`${API_BASE_URL}/recurring-schedules/${scheduleId}/pause`, {
    method: 'POST',
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(getErrorMessage(errData, 'Failed to pause recurring schedule'));
  }
  return res.json();
}

/**
 * Stage 2: Resumes a PAUSED recurring schedule (REC-08, A18).
 */
export async function resumeSchedule(scheduleId: string): Promise<RecurringSchedule> {
  const res = await fetch(`${API_BASE_URL}/recurring-schedules/${scheduleId}/resume`, {
    method: 'POST',
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(getErrorMessage(errData, 'Failed to resume recurring schedule'));
  }
  return res.json();
}

/**
 * Stage 2: Cancels a recurring schedule permanently (REC-07, A18).
 */
export async function cancelSchedule(scheduleId: string): Promise<RecurringSchedule> {
  const res = await fetch(`${API_BASE_URL}/recurring-schedules/${scheduleId}/cancel`, {
    method: 'POST',
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(getErrorMessage(errData, 'Failed to cancel recurring schedule'));
  }
  return res.json();
}
