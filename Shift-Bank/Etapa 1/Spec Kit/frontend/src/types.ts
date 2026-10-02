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
