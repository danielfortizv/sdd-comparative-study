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
  to_account_id: number;
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
