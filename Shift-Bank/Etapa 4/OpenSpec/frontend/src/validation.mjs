export function validateMoney(value, { positive = true } = {}) {
  if (typeof value !== 'string' || !/^(?:\d+(?:\.\d{0,2})?|\.\d{1,2})$/.test(value.trim())) return false;
  const [wholePart, fraction = ''] = value.trim().split('.');
  const cents = BigInt(wholePart || '0') * 100n + BigInt((fraction + '00').slice(0, 2));
  return positive ? cents > 0n : true;
}

export function routingNumberValid(value) {
  return /^\d{9}$/.test(value);
}

export function accountNumberValid(value) {
  return /^\d{4,17}$/.test(value);
}

export function validateLimits(perTransfer, daily) {
  return validateMoney(perTransfer) && validateMoney(daily);
}

export function validateRecipient(value) {
  if (!value?.name?.trim()) return 'Beneficiary name is required.';
  if (!value?.bank_name?.trim()) return 'Bank name is required.';
  if (!routingNumberValid(value.routing_number)) return 'Routing number must contain exactly 9 numeric digits.';
  if (!accountNumberValid(value.account_number)) return 'Account number must contain 4 to 17 numeric digits.';
  return '';
}

export function transferLabel(type) {
  return type === 'ach' ? 'External ACH transfer' : type === 'recurring_ach' ? 'Recurring ACH transfer' : type === 'recurring_internal' ? 'Recurring internal transfer' : 'Internal transfer';
}

export function scheduleActionAllowed(status, action) {
  return action === 'pause' ? status === 'active' : action === 'resume' ? status === 'paused' : action === 'cancel' ? status === 'active' || status === 'paused' : false;
}

export function statusLabel(status) {
  return ({ PENDING_MFA: 'Awaiting MFA', pending: 'Pending', settled: 'Settled', failed: 'Failed', COMPLETED: 'Completed', EXPIRED: 'Expired', active: 'Active', paused: 'Paused', cancelled: 'Cancelled' })[status] || status;
}
