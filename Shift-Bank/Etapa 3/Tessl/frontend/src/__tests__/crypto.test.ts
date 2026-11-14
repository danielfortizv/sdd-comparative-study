import { describe, it, expect, vi, beforeEach } from 'vitest';
import { encryptField, getActiveServerPublicKey, invalidatePublicKeyCache } from '../api/crypto';
import { api } from '../api/client';

describe('Frontend Web Crypto Client', () => {
  beforeEach(() => {
    invalidatePublicKeyCache();
    vi.restoreAllMocks();
  });

  it('fetches server public key and encrypts sensitive fields into EncryptedFieldPayload envelope', async () => {
    const keyPair = await globalThis.crypto.subtle.generateKey(
      {
        name: 'RSA-OAEP',
        modulusLength: 2048,
        publicExponent: new Uint8Array([1, 0, 1]),
        hash: 'SHA-256',
      },
      true,
      ['encrypt', 'decrypt']
    );

    const exportedSpki = await globalThis.crypto.subtle.exportKey('spki', keyPair.publicKey);
    const b64 = btoa(String.fromCharCode(...new Uint8Array(exportedSpki)));
    const pem = `-----BEGIN PUBLIC KEY-----\n${b64}\n-----END PUBLIC KEY-----`;

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        key_id: 'test_key_123',
        algorithm: 'RSA-OAEP-256',
        public_key: pem,
        expires_at: new Date(Date.now() + 86400000).toISOString(),
      }),
    });

    const envelope = await encryptField('123456789');

    expect(envelope.__encrypted__).toBe(true);
    expect(envelope.key_id).toBe('test_key_123');
    expect(typeof envelope.encrypted_key).toBe('string');
    expect(typeof envelope.iv).toBe('string');
    expect(typeof envelope.ciphertext).toBe('string');
    expect(typeof envelope.tag).toBe('string');

    // Decrypt in test using private key to verify cryptographic roundtrip
    const encKeyBytes = Uint8Array.from(atob(envelope.encrypted_key), c => c.charCodeAt(0));
    const decryptedSessionKeyRaw = await globalThis.crypto.subtle.decrypt(
      { name: 'RSA-OAEP' },
      keyPair.privateKey,
      encKeyBytes
    );

    const sessionKey = await globalThis.crypto.subtle.importKey(
      'raw',
      decryptedSessionKeyRaw,
      { name: 'AES-GCM' },
      false,
      ['decrypt']
    );

    const ivBytes = Uint8Array.from(atob(envelope.iv), c => c.charCodeAt(0));
    const ctBytes = Uint8Array.from(atob(envelope.ciphertext), c => c.charCodeAt(0));
    const tagBytes = Uint8Array.from(atob(envelope.tag), c => c.charCodeAt(0));

    const combinedCiphertext = new Uint8Array(ctBytes.length + tagBytes.length);
    combinedCiphertext.set(ctBytes, 0);
    combinedCiphertext.set(tagBytes, ctBytes.length);

    const decryptedPlaintextBuffer = await globalThis.crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: ivBytes, tagLength: 128 },
      sessionKey,
      combinedCiphertext
    );

    const decryptedText = new TextDecoder().decode(decryptedPlaintextBuffer);
    expect(decryptedText).toBe('123456789');
  });

  it('handles public key fetch failure gracefully', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
    });

    await expect(getActiveServerPublicKey()).rejects.toThrow('Failed to fetch public key: 500');
  });

  it('never sends plaintext over HTTP when client encryption fails', async () => {
    // Simulate encryption failure by failing public key fetch
    const fetchMock = vi.fn().mockImplementation(async (url: string) => {
      if (url.includes('/api/crypto/public-key')) {
        return {
          ok: false,
          status: 500,
          json: async () => ({ detail: 'Server crypto error' }),
        };
      }
      return {
        ok: true,
        status: 201,
        json: async () => ({ id: 1 }),
      };
    });
    globalThis.fetch = fetchMock;

    await expect(
      api.createBeneficiary({
        name: 'Secret Vendor',
        routing_number: '123456789',
        account_number: '9876543210',
        bank_name: 'Secure Bank',
      })
    ).rejects.toThrow('Client-side encryption failure');

    // Verify /api/beneficiaries was NEVER called with plaintext
    const beneficiaryCalls = fetchMock.mock.calls.filter(call =>
      call[0].includes('/api/beneficiaries')
    );
    expect(beneficiaryCalls.length).toBe(0);
  });

  it('retries with refreshed public key when server returns KEY_EXPIRED without sending plaintext', async () => {
    // Generate two key pairs (old and new)
    const keyPairNew = await globalThis.crypto.subtle.generateKey(
      {
        name: 'RSA-OAEP',
        modulusLength: 2048,
        publicExponent: new Uint8Array([1, 0, 1]),
        hash: 'SHA-256',
      },
      true,
      ['encrypt', 'decrypt']
    );
    const spkiNew = await globalThis.crypto.subtle.exportKey('spki', keyPairNew.publicKey);
    const pemNew = `-----BEGIN PUBLIC KEY-----\n${btoa(String.fromCharCode(...new Uint8Array(spkiNew)))}\n-----END PUBLIC KEY-----`;

    let attempt = 0;
    const fetchMock = vi.fn().mockImplementation(async (url: string, opts?: RequestInit) => {
      if (url.includes('/api/crypto/public-key')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            key_id: attempt === 0 ? 'k_old' : 'k_new',
            algorithm: 'RSA-OAEP-256',
            public_key: pemNew,
            expires_at: new Date(Date.now() + 86400000).toISOString(),
          }),
        };
      }

      if (url.includes('/api/beneficiaries')) {
        attempt++;
        const body = JSON.parse(opts?.body as string);
        // Verify payload is ALWAYS encrypted, never plaintext
        expect(body.routing_number.__encrypted__).toBe(true);
        expect(body.account_number.__encrypted__).toBe(true);

        if (attempt === 1) {
          // First attempt rejects with KEY_EXPIRED
          return {
            ok: false,
            status: 400,
            json: async () => ({ detail: 'KEY_EXPIRED' }),
          };
        }

        // Second attempt succeeds with new key
        return {
          ok: true,
          status: 201,
          json: async () => ({
            id: 1,
            user_id: 1,
            name: body.name,
            routing_number: '123456789',
            account_number: '9876543210',
            bank_name: body.bank_name,
            created_at: new Date().toISOString(),
          }),
        };
      }

      return { ok: false, status: 404 };
    });

    globalThis.fetch = fetchMock;

    const res = await api.createBeneficiary({
      name: 'Vendor A',
      routing_number: '123456789',
      account_number: '9876543210',
      bank_name: 'Test Bank',
    });

    expect(res.id).toBe(1);
    expect(attempt).toBe(2);
  });
});
