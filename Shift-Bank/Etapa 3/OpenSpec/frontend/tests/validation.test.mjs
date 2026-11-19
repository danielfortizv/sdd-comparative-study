import test from 'node:test';
import assert from 'node:assert/strict';
import { validateMoney, routingNumberValid, accountNumberValid, validateLimits, validateRecipient, transferLabel, scheduleActionAllowed, statusLabel } from '../src/validation.mjs';
import { startRefreshPolling } from '../src/refreshPolling.mjs';
import { apiRequest, assertSecureTransport } from '../src/api.mjs';

test('sensitive browser API paths require HTTPS and fail before sending', async () => {
  assert.throws(() => assertSecureTransport('/api/beneficiaries', 'http:'), /require a secure HTTPS/);
  assert.throws(() => assertSecureTransport('/api/ach-transfers', 'http:'), /require a secure HTTPS/);
  assert.throws(() => assertSecureTransport('/api/recurring-schedules', 'http:'), /require a secure HTTPS/);
  let sent = false;
  await assert.rejects(apiRequest('/api/beneficiaries', {}, { protocol: 'http:', fetchImpl: async () => { sent = true; } }), /require a secure HTTPS/);
  assert.equal(sent, false);
});

test('sensitive browser API request uses HTTPS and does not expose protected transport errors', async () => {
  let captured;
  const result = await apiRequest('/api/ach-transfers', { method: 'POST', body: '{"account_number":"1234"}' }, {
    protocol: 'https:', fetchImpl: async (url, options) => {
      captured = { url, options };
      return { ok: true, status: 202, json: async () => ({ status: 'pending' }) };
    }
  });
  assert.equal(captured.url, '/api/ach-transfers');
  assert.equal(captured.options.method, 'POST');
  assert.equal(result.status, 'pending');
});

test('API reports safe key-provisioning errors without sending plaintext over HTTP', async () => {
  let message;
  try {
    await apiRequest('/api/beneficiaries', {}, {
      protocol: 'https:', fetchImpl: async () => ({ ok: false, status: 503, json: async () => ({ detail: 'Sensitive data protection key is unavailable' }) })
    });
  } catch (error) { message = error; }
  assert.ok(message instanceof Error);
  assert.match(message.message, /key is unavailable/i);
  assert.doesNotMatch(message.message, /123456789|secret|private key/i);
});

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
