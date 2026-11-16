// Tipos compartidos de la UI. Los montos siempre son `string` (decimal-string),
// nunca `number`, para preservar la exactitud decimal (Requisito 3.5).

export type AccountKind = "checking" | "savings";

export interface Account {
  name: string; // nombre amigable: "Checking" | "Savings"
  balance: string; // decimal-string
}

export interface AccountsResponse {
  accounts: Account[];
}

export type TransferStatus = "PENDING_MFA" | "COMPLETED" | "FAILED" | "EXPIRED";

export interface CreateTransferRequest {
  from: AccountKind;
  to: AccountKind;
  amount: string; // decimal-string
  description: string;
}

export interface CreateTransferResponse {
  status: TransferStatus;
  mfa_required: boolean;
  reference?: string | null;
  expires_at?: string | null;
}

export interface MfaResponse {
  status: TransferStatus;
}

export interface TransferHistoryItem {
  date: string;
  direction: { from: string; to: string };
  amount: string; // decimal-string
  description: string;
  status: TransferStatus;
}

export interface TransfersHistoryResponse {
  transfers: TransferHistoryItem[];
}

export interface ApiError {
  code: string;
  message: string;
}
