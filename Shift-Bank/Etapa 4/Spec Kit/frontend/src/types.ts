export interface Account {
  id: string;
  name: string;
  balance: string;
  currency: string;
  version?: number;
}

export interface Transfer {
  id: string;
  source_account: string;
  destination_account: string;
  amount: string;
  status: 'PENDING_MFA' | 'COMPLETED' | 'FAILED' | 'EXPIRED';
  created_at: string;
  expires_at: string | null;
  source_version?: number;
  destination_version?: number;
  source_account_id?: string;
  destination_account_id?: string;
  currency?: string;
  transfer_type?: 'INTERNAL' | 'ACH';
}

export interface HistoryEntry {
  id: string;
  direction: 'incoming' | 'outgoing';
  amount: string;
  description: string;
  date: string;
  currency?: string;
  counter_amount?: string | null;
  counter_currency?: string | null;
  rate_numerator?: number | null;
  rate_denominator?: number | null;
}

export interface MFAConfirmResponse {
  id: string;
  status: string;
  message: string;
}

export interface ApiError {
  detail: string;
  code?: string;
  status?: number;
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
  expected_versions: Record<string, number>;
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
  currency?: string;
  source_version?: number;
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
  currency?: string;
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
  expected_versions: Record<string, number>;
}

export interface ConversionResponse {
  id: string;
  source_account_id: string;
  destination_account_id: string;
  source_amount: string;
  source_currency: string;
  destination_amount: string;
  destination_currency: string;
  rate_numerator: number;
  rate_denominator: number;
  source_version: number;
  destination_version: number;
}

// Stage 3: Application-Layer Encryption & Deployment (E3-ENC-01, E3-AUD-01, E3-DEP-01)
export interface CryptographicEnvelope {
  encrypted_key: string;
  iv: string;
  ciphertext: string;
  tag: string;
}

export interface PublicKeyResponse {
  algorithm: string;
  format: string;
  public_key: string;
  key_id?: string;
}

export interface AuditRecord {
  id: number;
  timestamp: string;
  event_type: string;
  actor_id: string;
  resource_id: string | null;
  payload_digest: string;
  previous_hash: string;
  record_hmac: string;
}

export interface AuditVerificationResponse {
  is_valid: boolean;
  verified_records: number;
  latest_sequence: number;
  latest_hash: string;
  details: string;
  broken_sequence?: number | null;
  tail_truncation_detected?: boolean;
  expected_head?: string | null;
}

export interface HealthResponse {
  status: string;
  database: string;
  scheduler_active: boolean;
  crypto_keys_loaded: boolean;
  environment?: string;
}

