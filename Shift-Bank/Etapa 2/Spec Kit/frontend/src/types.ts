export interface Account {
  id: string;
  name: string;
  balance: string;
  currency: string;
}

export interface Transfer {
  id: string;
  source_account: string;
  destination_account: string;
  amount: string;
  status: 'PENDING_MFA' | 'COMPLETED' | 'FAILED' | 'EXPIRED';
  created_at: string;
  expires_at: string | null;
}

export interface HistoryEntry {
  id: string;
  direction: 'incoming' | 'outgoing';
  amount: string;
  description: string;
  date: string;
}

export interface MFAConfirmResponse {
  id: string;
  status: string;
  message: string;
}

export interface ApiError {
  detail: string;
}

// Stage 2: Dynamic Limits (LIM-01..09, D-01, D-07)
export interface LimitResponse {
  per_transfer_limit: string;
  daily_limit: string;
  current_daily_consumption: string;
  remaining_daily_availability: string;
  updated_at: string;
}

export interface LimitUpdate {
  per_transfer_limit: string;
  daily_limit: string;
}

// Stage 2: External ACH Beneficiaries (ACH-01..03, D-08)
export interface Beneficiary {
  id: string;
  name: string;
  bank_name: string;
  routing_number: string;
  account_number: string;
  created_at: string;
}

export interface BeneficiaryCreate {
  name: string;
  bank_name: string;
  routing_number: string;
  account_number: string;
}

// Stage 2: ACH Transfers (ACH-04..10, D-06)
export interface AchTransferCreate {
  source_account_id: string;
  amount: string;
  recipient_name: string;
  bank_name: string;
  routing_number: string;
  account_number: string;
  save_beneficiary: boolean;
}

export interface AchTransferResponse {
  id: string;
  transfer_type: 'ACH';
  source_account: string;
  recipient_name: string;
  bank_name: string;
  routing_number: string;
  account_number: string;
  amount: string;
  status: 'PENDING' | 'PENDING_MFA' | 'SETTLED' | 'FAILED';
  created_at: string;
  expires_at?: string | null;
}

// Stage 2: Recurring Schedules (REC-01..12, D-03, D-05, D-09)
export type RecurringFrequency = 'DAILY' | 'WEEKLY' | 'MONTHLY';
export type RecurringStatus = 'ACTIVE' | 'PENDING_MFA' | 'PAUSED' | 'CANCELLED' | 'EXPIRED';

export interface RecurringSchedule {
  id: string;
  transfer_type: 'INTERNAL' | 'ACH';
  source_account_id: string;
  source_account: string;
  destination_display: string;
  amount: string;
  frequency: RecurringFrequency;
  status: RecurringStatus;
  next_due_date: string;
  last_executed_at: string | null;
  mfa_expires_at: string | null;
  created_at: string;
}

export interface RecurringScheduleCreate {
  transfer_type: 'INTERNAL' | 'ACH';
  source_account_id: string;
  amount: string;
  frequency: RecurringFrequency;
  start_date?: string; // YYYY-MM-DD
  destination_account_id?: string;
  recipient_name?: string;
  bank_name?: string;
  routing_number?: string;
  account_number?: string;
}
