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
} from './types';

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
 * Can return 200 OK (Completed) or 202 Accepted (Pending MFA).
 */
export async function initiateTransfer(
  sourceAccountId: string,
  destinationAccountId: string,
  amount: string
): Promise<Transfer> {
  const res = await fetch(`${API_BASE_URL}/transfers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source_account_id: sourceAccountId,
      destination_account_id: destinationAccountId,
      amount,
    }),
  });

  if (!res.ok && res.status !== 202) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(getErrorMessage(errData, 'Failed to initiate transfer'));
  }
  return res.json();
}

/**
 * Submits the MFA verification code to finalize a sensitive internal or ACH transfer.
 */
export async function confirmMFA(
  transferId: string,
  code: string
): Promise<MFAConfirmResponse> {
  const res = await fetch(`${API_BASE_URL}/transfers/${transferId}/confirm-mfa`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(getErrorMessage(errData, 'Failed to verify MFA code'));
  }
  return res.json();
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
 */
export async function updateLimits(payload: LimitUpdate): Promise<LimitResponse> {
  const res = await fetch(`${API_BASE_URL}/limits`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
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
 */
export async function createBeneficiary(payload: BeneficiaryCreate): Promise<Beneficiary> {
  const res = await fetch(`${API_BASE_URL}/beneficiaries`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
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
 * Can return 201 Created (Pending settlement) or 202 Accepted (Pending MFA).
 */
export async function initiateAchTransfer(payload: AchTransferCreate): Promise<AchTransferResponse> {
  const res = await fetch(`${API_BASE_URL}/transfers/ach`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok && res.status !== 202) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(getErrorMessage(errData, 'Failed to initiate ACH transfer'));
  }
  return res.json();
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
 * Can return 201 Created (ACTIVE) or 202 Accepted (PENDING_MFA).
 */
export async function createSchedule(payload: RecurringScheduleCreate): Promise<RecurringSchedule> {
  const res = await fetch(`${API_BASE_URL}/recurring-schedules`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok && res.status !== 202) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(getErrorMessage(errData, 'Failed to create recurring schedule'));
  }
  return res.json();
}

/**
 * Stage 2: Confirms MFA code for a sensitive recurring schedule (D-03, D-05).
 */
export async function confirmScheduleMFA(scheduleId: string, code: string): Promise<RecurringSchedule> {
  const res = await fetch(`${API_BASE_URL}/recurring-schedules/${scheduleId}/confirm-mfa`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(getErrorMessage(errData, 'Failed to verify schedule MFA code'));
  }
  return res.json();
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
