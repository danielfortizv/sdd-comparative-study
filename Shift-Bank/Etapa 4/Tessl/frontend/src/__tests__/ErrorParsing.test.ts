import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api, ApiError } from '../api/client';

describe('HTTP Client Boundary Error Parsing', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('parses top-level {code, message, detail} into structured ApiError without stringifying JSON', async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      status: 409,
      statusText: 'Conflict',
      json: async () => ({
        code: 'ACCOUNT_VERSION_CONFLICT',
        message: 'Account CHK-1001 version mismatch. Expected 1, found 2',
        detail: {
          account_id: 1,
          account_number: 'CHK-1001',
          expected_version: 1,
          current_version: 2,
        },
      }),
    } as any);

    try {
      await api.executeTransfer({
        from_account_id: 1,
        to_account_id: 2,
        amount: '50.00',
        expected_from_version: 1,
        expected_to_version: 1,
      });
      expect.unreachable('Should have thrown ApiError');
    } catch (err: any) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.status).toBe(409);
      expect(err.code).toBe('ACCOUNT_VERSION_CONFLICT');
      expect(err.message).toBe('Account CHK-1001 version mismatch. Expected 1, found 2');
      expect(err.detail).toEqual({
        account_id: 1,
        account_number: 'CHK-1001',
        expected_version: 1,
        current_version: 2,
      });
    }
  });

  it('parses FastAPI nested {detail: {code, message}} into structured ApiError', async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      status: 409,
      statusText: 'Conflict',
      json: async () => ({
        detail: {
          code: 'IDEMPOTENCY_KEY_REUSE',
          message: 'Idempotency key was previously committed with different request parameters',
        },
      }),
    } as any);

    try {
      await api.executeTransfer({
        from_account_id: 1,
        to_account_id: 2,
        amount: '50.00',
        expected_from_version: 1,
        expected_to_version: 1,
      });
      expect.unreachable('Should have thrown ApiError');
    } catch (err: any) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.status).toBe(409);
      expect(err.code).toBe('IDEMPOTENCY_KEY_REUSE');
      expect(err.message).toBe('Idempotency key was previously committed with different request parameters');
      expect(err.detail.code).toBe('IDEMPOTENCY_KEY_REUSE');
    }
  });

  it('parses legacy string {detail: "..."} into ApiError with clean message', async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: async () => ({
        detail: 'Invalid Security PIN',
      }),
    } as any);

    try {
      await api.verifyMfa('0000');
      expect.unreachable('Should have thrown ApiError');
    } catch (err: any) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.status).toBe(400);
      expect(err.code).toBe('ERROR');
      expect(err.message).toBe('Invalid Security PIN');
    }
  });

  it('parses HTTP 423 LOCKED into ApiError with lockout message', async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      status: 423,
      statusText: 'Locked',
      json: async () => ({
        detail: 'MFA verification is locked due to 3 failed attempts. Please contact support.',
      }),
    } as any);

    try {
      await api.verifyMfa('1234');
      expect.unreachable('Should have thrown ApiError');
    } catch (err: any) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.status).toBe(423);
      expect(err.message).toBe('MFA verification is locked due to 3 failed attempts. Please contact support.');
    }
  });

  it('parses HTTP 500 IDEMPOTENT_RECORD_CORRUPTED with structured error code and message', async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: async () => ({
        code: 'IDEMPOTENT_RECORD_CORRUPTED',
        message: 'Idempotent record exists but underlying Transfer entity could not be resolved',
      }),
    } as any);

    try {
      await api.executeTransfer({
        from_account_id: 1,
        to_account_id: 2,
        amount: '50.00',
        expected_from_version: 1,
        expected_to_version: 1,
      });
      expect.unreachable('Should have thrown ApiError');
    } catch (err: any) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.status).toBe(500);
      expect(err.code).toBe('IDEMPOTENT_RECORD_CORRUPTED');
      expect(err.message).toBe('Idempotent record exists but underlying Transfer entity could not be resolved');
    }
  });

  it('handles transport failure (Failed to fetch) and produces NETWORK_ERROR with status 0', async () => {
    globalThis.fetch = vi.fn().mockRejectedValueOnce(new TypeError('Failed to fetch'));

    try {
      await api.getAccounts();
      expect.unreachable('Should have thrown ApiError');
    } catch (err: any) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.status).toBe(0);
      expect(err.code).toBe('NETWORK_ERROR');
      expect(err.message).toContain('Failed to fetch');
    }
  });

  it('handles non-JSON error (HTML 502 Bad Gateway) using statusText fallback', async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      status: 502,
      statusText: 'Bad Gateway',
      json: async () => {
        throw new SyntaxError('Unexpected token < in JSON at position 0');
      },
    } as any);

    try {
      await api.getAccounts();
      expect.unreachable('Should have thrown ApiError');
    } catch (err: any) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.status).toBe(502);
      expect(err.message).toBe('Bad Gateway');
    }
  });
});
