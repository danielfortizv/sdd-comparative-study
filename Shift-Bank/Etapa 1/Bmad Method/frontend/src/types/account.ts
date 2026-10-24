export type AccountType = 'CHECKING' | 'SAVINGS' | 'RESERVE';

export interface Account {
  id: string;
  nickname: string;
  type: AccountType;
  account_type: AccountType;
  balance_cents: number;
  balance_formatted: string;
}
