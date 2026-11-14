export interface Account {
  id: number;
  user_id: number;
  account_number: string;
  account_type: 'checking' | 'savings';
  account_name: string;
  balance: string;
  currency: string;
  version: number;
  created_at: string;
}

export interface TransferRequest {
  from_account_id: number;
  to_account_id: number;
  amount: string;
  expected_from_version: number;
  expected_to_version: number;
  description?: string;
  pin?: string;
}

export interface TransferResponse {
  id: number;
  operation_id?: string;
  from_account_id: number;
  to_account_id?: number | null;
  amount: string;
  currency?: string;
  from_account_version?: number;
  to_account_version?: number;
  status: string;
  description?: string;
  created_at: string;
}

export interface ConversionRequest {
  from_account_id: number;
  to_account_id: number;
  source_amount: string;
  expected_from_version: number;
  expected_to_version: number;
  description?: string;
  pin?: string;
}

export interface ConversionResponse {
  id: number;
  operation_id: string;
  from_account_id: number;
  to_account_id: number;
  source_currency: string;
  destination_currency: string;
  source_amount: string;
  destination_amount: string;
  exchange_rate_display: string;
  rate_numerator: number;
  rate_denominator: number;
  rate_version: string;
  rounding_residual: string;
  from_account_version: number;
  to_account_version: number;
  status: string;
  description?: string;
  created_at: string;
}

export interface Transaction {
  id: number;
  account_id: number;
  account_name?: string;
  transfer_id?: number | null;
  conversion_id?: number | null;
  transaction_type: 'credit' | 'debit';
  amount: string;
  balance_after: string;
  currency?: string;
  description: string;
  reference?: string | null;
  source_amount?: string | null;
  source_currency?: string | null;
  destination_amount?: string | null;
  destination_currency?: string | null;
  exchange_rate_display?: string | null;
  status?: 'completed' | 'pending' | 'failed';
  created_at: string;
}

export interface MfaStatus {
  threshold: string;
  locked: boolean;
  remaining_attempts: number;
}

export interface MfaVerifyResponse {
  valid: boolean;
  remaining_attempts: number;
  locked: boolean;
}

// ==========================================
// Stage 3 Interfaces
// ==========================================

export interface PublicKeyResponse {
  key_id: string;
  algorithm: string;
  public_key: string;
  expires_at: string;
}

export interface EncryptedFieldPayload {
  __encrypted__: true;
  key_id: string;
  encrypted_key: string;
  iv: string;
  ciphertext: string;
  tag: string;
}

// ==========================================
// Stage 2 Interfaces
// ==========================================

export interface Beneficiary {
  id: number;
  user_id: number;
  name: string;
  routing_number: string;
  account_number: string;
  bank_name: string;
  created_at: string;
}

export interface BeneficiaryCreateRequest {
  name: string;
  routing_number: string | EncryptedFieldPayload;
  account_number: string | EncryptedFieldPayload;
  bank_name: string;
}

export interface AchTransferRequest {
  from_account_id: number;
  amount: string;
  expected_from_version: number;
  description?: string;
  pin?: string;
  beneficiary_id?: number;
  recipient_name?: string;
  routing_number?: string | EncryptedFieldPayload;
  account_number?: string | EncryptedFieldPayload;
  bank_name?: string;
  save_beneficiary?: boolean;
}

export interface AchTransferResponse {
  id: number;
  operation_id?: string;
  from_account_id: number;
  from_account_version?: number;
  beneficiary_id?: number | null;
  recipient_name: string;
  routing_number: string;
  account_number: string;
  bank_name: string;
  amount: string;
  currency?: string;
  status: 'pending' | 'settled' | 'failed';
  description?: string;
  created_at: string;
  settled_at?: string | null;
}

export interface RecurringSchedule {
  id: number;
  user_id: number;
  transfer_type: 'internal' | 'ach';
  from_account_id: number;
  to_account_id?: number | null;
  beneficiary_id?: number | null;
  recipient_name?: string | null;
  routing_number?: string | null;
  account_number?: string | null;
  bank_name?: string | null;
  amount: string;
  currency?: string;
  frequency: 'daily' | 'weekly' | 'monthly';
  status: 'active' | 'paused' | 'cancelled';
  description?: string | null;
  next_execution_date: string;
  created_at: string;
  last_executed_at?: string | null;
}

export interface RecurringScheduleCreateRequest {
  transfer_type: 'internal' | 'ach';
  from_account_id: number;
  to_account_id?: number;
  beneficiary_id?: number;
  recipient_name?: string;
  routing_number?: string | EncryptedFieldPayload;
  account_number?: string | EncryptedFieldPayload;
  bank_name?: string;
  amount: string;
  frequency: 'daily' | 'weekly' | 'monthly';
  start_date?: string;
  description?: string;
  pin?: string;
}

export interface TransferLimits {
  per_transaction_limit: string;
  daily_limit: string;
  current_daily_total: string;
  remaining_daily_limit: string;
  reference_currency?: string;
}

export interface TransferLimitsUpdateRequest {
  per_transaction_limit: string;
  daily_limit: string;
}

export interface ErrorResponse {
  code?: string;
  message?: string;
  detail?: any;
}
