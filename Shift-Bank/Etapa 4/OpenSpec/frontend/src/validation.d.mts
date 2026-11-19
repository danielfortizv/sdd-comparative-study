export function validateMoney(value: string, options?: { positive?: boolean }): boolean;
export function routingNumberValid(value: string): boolean;
export function accountNumberValid(value: string): boolean;
export function validateLimits(perTransfer: string, daily: string): boolean;
export function validateRecipient(value: { name: string; bank_name: string; routing_number: string; account_number: string }): string;
export function transferLabel(type?: string): string;
export function scheduleActionAllowed(status: string, action: string): boolean;
export function statusLabel(status: string): string;
