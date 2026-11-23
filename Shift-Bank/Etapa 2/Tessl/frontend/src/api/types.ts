export interface Account {
  id: number;
  user_id: number;
  account_number: string;
  account_type: 'checking' | 'savings';
  account_name: string;
  balance: number;
  currency: string;
  created_at: string;
}

export interface TransferRequest {
  from_account_id: number;
  to_account_id: number;
  amount: number;
  description?: string;
  pin?: string;
}

export interface TransferResponse {
  id: number;
  from_account_id: number;
  to_account_id?: number | null;
  amount: number;
  status: string;
  description?: string;
  created_at: string;
}

export interface Transaction {
  id: number;
  account_id: number;
  account_name?: string;
  transfer_id?: number | null;
  transaction_type: 'credit' | 'debit';
  amount: number;
  balance_after: number;
  description: string;
  reference?: string | null;
  status?: 'completed' | 'pending' | 'failed';
  created_at: string;
}

export interface MfaStatus {
  threshold: number;
  locked: boolean;
  remaining_attempts: number;
}

export interface MfaVerifyResponse {
  valid: boolean;
  remaining_attempts: number;
  locked: boolean;
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
  routing_number: string;
  account_number: string;
  bank_name: string;
}

export interface AchTransferRequest {
  from_account_id: number;
  amount: number;
  description?: string;
  pin?: string;
  beneficiary_id?: number;
  recipient_name?: string;
  routing_number?: string;
  account_number?: string;
  bank_name?: string;
  save_beneficiary?: boolean;
}

export interface AchTransferResponse {
  id: number;
  from_account_id: number;
  beneficiary_id?: number | null;
  recipient_name: string;
  routing_number: string;
  account_number: string;
  bank_name: string;
  amount: number;
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
  amount: number;
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
  routing_number?: string;
  account_number?: string;
  bank_name?: string;
  amount: number;
  frequency: 'daily' | 'weekly' | 'monthly';
  start_date?: string;
  description?: string;
  pin?: string;
}

export interface TransferLimits {
  per_transaction_limit: number;
  daily_limit: number;
  current_daily_total: number;
  remaining_daily_limit: number;
}

export interface TransferLimitsUpdateRequest {
  per_transaction_limit: number;
  daily_limit: number;
}
