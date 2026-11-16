import { afterEach, describe, expect, test, vi } from 'vitest';
import { confirmMFA, initiateTransfer } from './services';
import { encryptPayload } from './crypto';

vi.mock('./crypto', () => ({
  encryptPayload: vi.fn(async () => ({ encrypted_key: 'key', iv: 'iv', ciphertext: 'cipher', tag: 'tag' })),
}));

afterEach(() => vi.unstubAllGlobals());

describe('Stage 4 encrypted command transport', () => {
  test('sends transfer versions under a stable UUID header in an encrypted envelope', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({ id: 'tr-1', source_account: 'Checking', destination_account: 'Savings', amount: '1.00', status: 'COMPLETED', created_at: '2026-11-16T00:00:00Z', expires_at: null }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const versions = { 'CHK-1001': 7, 'SAV-2001': 3 };
    await initiateTransfer('CHK-1001', 'SAV-2001', '1.00', versions, '00000000-0000-4000-8000-000000000010');

    expect(encryptPayload).toHaveBeenCalledWith({
      source_account_id: 'CHK-1001', destination_account_id: 'SAV-2001', amount: '1.00', expected_versions: versions,
    });
    const [url, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('http://127.0.0.1:8000/api/transfers');
    expect((request.headers as Record<string, string>)['Idempotency-Key']).toBe('00000000-0000-4000-8000-000000000010');
    expect(JSON.parse(request.body as string)).toEqual({ encrypted_key: 'key', iv: 'iv', ciphertext: 'cipher', tag: 'tag' });
  });

  test('MFA confirmation uses the encrypted metadata endpoint and preserves typed conflict codes', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce({
      ok: true, status: 200, json: async () => ({ id: 'tr-1', status: 'COMPLETED', message: 'confirmed' }),
    }).mockResolvedValueOnce({
      ok: false, status: 409, json: async () => ({ detail: { code: 'ACCOUNT_VERSION_CONFLICT', message: 'stale' } }),
    });
    vi.stubGlobal('fetch', fetchMock);
    await confirmMFA('tr-1', '123456', { 'CHK-1001': 7 }, '00000000-0000-4000-8000-000000000011');
    const [url, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/transfers/tr-1/confirm-mfa');
    expect((request.headers as Record<string, string>)['Idempotency-Key']).toBe('00000000-0000-4000-8000-000000000011');
    await expect(confirmMFA('tr-1', '123456', { 'CHK-1001': 7 }, '00000000-0000-4000-8000-000000000012'))
      .rejects.toMatchObject({ code: 'ACCOUNT_VERSION_CONFLICT', status: 409 });
  });
});
