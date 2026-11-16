import test from 'node:test';
import assert from 'node:assert/strict';
import { validateMoney, routingNumberValid, accountNumberValid, validateLimits, validateRecipient, transferLabel, scheduleActionAllowed, statusLabel } from '../src/validation.mjs';
import { startRefreshPolling } from '../src/refreshPolling.mjs';

test('money values allow positive COP precision to two decimal places', () => {
  for (const value of ['0.01', '.5', '1000000', '5000000.00']) assert.equal(validateMoney(value), true);
  for (const value of ['', '0', '-1', '1.001', '1e3', 'abc']) assert.equal(validateMoney(value), false);
});

test('routing and account formats enforce their digit counts', () => {
  assert.equal(routingNumberValid('123456789'), true);
  for (const value of ['12345678', '1234567890', '1234x6789']) assert.equal(routingNumberValid(value), false);
  assert.equal(accountNumberValid('1234'), true);
  assert.equal(accountNumberValid('12345678901234567'), true);
  for (const value of ['123', '123456789012345678', '12x4']) assert.equal(accountNumberValid(value), false);
});

test('limit settings and beneficiary validation return actionable outcomes', () => {
  assert.equal(validateLimits('5000000.00', '10000000.00'), true);
  assert.equal(validateLimits('0', '10000000'), false);
  assert.equal(validateLimits('5000000.001', '10000000'), false);
  const valid = { name: 'A', bank_name: 'B', routing_number: '123456789', account_number: '1234' };
  assert.equal(validateRecipient(valid), '');
  assert.match(validateRecipient({ ...valid, routing_number: '123' }), /routing number/i);
  assert.match(validateRecipient({ ...valid, account_number: '123' }), /account number/i);
});

test('history and schedule helpers preserve visible transfer distinctions and terminal cancellation', () => {
  assert.equal(transferLabel('internal'), 'Internal transfer');
  assert.equal(transferLabel('ach'), 'External ACH transfer');
  assert.equal(transferLabel('recurring_ach'), 'Recurring ACH transfer');
  assert.equal(scheduleActionAllowed('cancelled', 'resume'), false);
  assert.equal(scheduleActionAllowed('paused', 'resume'), true);
  assert.equal(statusLabel('pending'), 'Pending');
  assert.equal(statusLabel('settled'), 'Settled');
  assert.equal(statusLabel('failed'), 'Failed');
  assert.equal(statusLabel('PENDING_MFA'), 'Awaiting MFA');
});

test('status refresh polling repeats and can be stopped when the app unmounts', async () => {
  let calls = 0;
  const cancel = startRefreshPolling(() => { calls += 1; }, 5);
  await new Promise(resolve => setTimeout(resolve, 25));
  cancel();
  const stoppedAt = calls;
  await new Promise(resolve => setTimeout(resolve, 15));
  assert.ok(stoppedAt >= 2);
  assert.equal(calls, stoppedAt);
});
