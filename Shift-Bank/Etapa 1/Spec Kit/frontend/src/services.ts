import { Account, Transfer, HistoryEntry, MFAConfirmResponse } from './types';

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
 * Initiates a standard or sensitive fund transfer.
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
 * Submits the MFA verification code to finalize a sensitive transfer.
 */
export async function confirmMFA(
  transferId: string,
  code: string
): Promise<MFAConfirmResponse> {
  const res = await fetch(`${API_BASE_URL}/transfers/${transferId}/mfa`, {
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
