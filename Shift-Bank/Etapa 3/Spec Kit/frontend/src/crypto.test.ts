import { describe, it, expect, beforeEach, vi } from 'vitest';
import { encryptPayload, clearPublicKeyCache } from './crypto';

describe('Frontend Crypto Wrapper (Web Crypto API)', () => {
  beforeEach(() => {
    clearPublicKeyCache();
    vi.restoreAllMocks();
  });

  it('fetches public key and generates valid CryptographicEnvelope with base64 fields', async () => {
    // Generate a test RSA keypair using Web Crypto
    const rsaKeypair = await window.crypto.subtle.generateKey(
      {
        name: 'RSA-OAEP',
        modulusLength: 2048,
        publicExponent: new Uint8Array([1, 0, 1]),
        hash: 'SHA-256',
      },
      true,
      ['encrypt', 'decrypt']
    );

    const exportedSpki = await window.crypto.subtle.exportKey('spki', rsaKeypair.publicKey);
    const spkiBytes = new Uint8Array(exportedSpki);
    let binary = '';
    for (let i = 0; i < spkiBytes.byteLength; i++) {
      binary += String.fromCharCode(spkiBytes[i]);
    }
    const b64 = window.btoa(binary);
    const mockPem = `-----BEGIN PUBLIC KEY-----\n${b64}\n-----END PUBLIC KEY-----\n`;

    // Mock fetch for /api/crypto/public-key
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        algorithm: 'RSA-OAEP-256',
        format: 'PEM',
        public_key: mockPem,
      }),
    });

    const payload = {
      source_account_id: 'acc_checking_123',
      destination_account_id: 'acc_savings_456',
      amount: '150000.00',
    };

    const envelope = await encryptPayload(payload);

    // Verify envelope attributes
    expect(envelope).toBeDefined();
    expect(typeof envelope.encrypted_key).toBe('string');
    expect(typeof envelope.iv).toBe('string');
    expect(typeof envelope.ciphertext).toBe('string');
    expect(typeof envelope.tag).toBe('string');

    // Verify base64 decodability and lengths
    const wrappedKeyBytes = window.atob(envelope.encrypted_key);
    expect(wrappedKeyBytes.length).toBe(256); // 2048-bit RSA produces 256 bytes

    const ivBytes = window.atob(envelope.iv);
    expect(ivBytes.length).toBe(12); // 12-byte IV

    const tagBytes = window.atob(envelope.tag);
    expect(tagBytes.length).toBe(16); // 16-byte GCM tag

    // Verify that decrypting with the private key recovers original payload
    const unwrappedAesKeyRaw = await window.crypto.subtle.decrypt(
      { name: 'RSA-OAEP' },
      rsaKeypair.privateKey,
      new Uint8Array([...wrappedKeyBytes].map((c) => c.charCodeAt(0)))
    );

    const importedAesKey = await window.crypto.subtle.importKey(
      'raw',
      unwrappedAesKeyRaw,
      { name: 'AES-GCM' },
      false,
      ['decrypt']
    );

    const ctBytes = window.atob(envelope.ciphertext);
    const fullCiphertext = new Uint8Array(ctBytes.length + tagBytes.length);
    for (let i = 0; i < ctBytes.length; i++) fullCiphertext[i] = ctBytes.charCodeAt(i);
    for (let i = 0; i < tagBytes.length; i++) fullCiphertext[ctBytes.length + i] = tagBytes.charCodeAt(i);

    const ivBuffer = new Uint8Array([...ivBytes].map((c) => c.charCodeAt(0)));
    const decryptedBuffer = await window.crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: ivBuffer },
      importedAesKey,
      fullCiphertext
    );

    const decryptedText = new TextDecoder().decode(decryptedBuffer);
    expect(JSON.parse(decryptedText)).toEqual(payload);
  });
});
