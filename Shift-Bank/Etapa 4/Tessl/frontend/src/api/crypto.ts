import { EncryptedFieldPayload, PublicKeyResponse } from './types';

// Cache for active public key: { key, expiresAt, keyId }
let cachedPublicKeyInfo: {
  key: CryptoKey;
  keyId: string;
  expiresAt: number;
} | null = null;

/**
 * Convert a base64 string to an ArrayBuffer.
 */
function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
}

/**
 * Convert an ArrayBuffer or Uint8Array to a base64 string.
 */
function arrayBufferToBase64(buffer: ArrayBuffer | Uint8Array): string {
  const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

/**
 * Parse an RSA SPKI public key from PEM string.
 */
function pemToArrayBuffer(pem: string): ArrayBuffer {
  const b64 = pem
    .replace(/-----BEGIN PUBLIC KEY-----/, '')
    .replace(/-----END PUBLIC KEY-----/, '')
    .replace(/\s+/g, '');
  return base64ToArrayBuffer(b64);
}

/**
 * Fetch and import active server RSA public key from the backend.
 */
export async function getActiveServerPublicKey(): Promise<{ key: CryptoKey; keyId: string }> {
  const now = Date.now();
  if (cachedPublicKeyInfo && cachedPublicKeyInfo.expiresAt > now + 60000) {
    return { key: cachedPublicKeyInfo.key, keyId: cachedPublicKeyInfo.keyId };
  }

  const res = await fetch('/api/crypto/public-key');
  if (!res.ok) {
    throw new Error(`Failed to fetch public key: ${res.status}`);
  }
  const data: PublicKeyResponse = await res.json();
  const spkiBuffer = pemToArrayBuffer(data.public_key);

  const subtle = (typeof window !== 'undefined' ? window.crypto : globalThis.crypto).subtle;
  const importedKey = await subtle.importKey(
    'spki',
    spkiBuffer,
    {
      name: 'RSA-OAEP',
      hash: 'SHA-256',
    },
    false,
    ['encrypt']
  );

  const expiresTimestamp = new Date(data.expires_at).getTime();
  cachedPublicKeyInfo = {
    key: importedKey,
    keyId: data.key_id,
    expiresAt: expiresTimestamp,
  };

  return { key: importedKey, keyId: data.key_id };
}

/**
 * Clear the public key cache (useful when receiving KEY_EXPIRED).
 */
export function invalidatePublicKeyCache(): void {
  cachedPublicKeyInfo = null;
}

/**
 * Encrypt a single sensitive field value using hybrid RSA-OAEP-256 and AES-256-GCM.
 */
export async function encryptField(plaintext: string): Promise<EncryptedFieldPayload> {
  const subtle = (typeof window !== 'undefined' ? window.crypto : globalThis.crypto).subtle;
  const cryptoObj = typeof window !== 'undefined' ? window.crypto : globalThis.crypto;

  // 1. Fetch server public key
  const { key: serverPublicKey, keyId } = await getActiveServerPublicKey();

  // 2. Generate ephemeral 256-bit AES-GCM session key
  const sessionKey = await subtle.generateKey(
    {
      name: 'AES-GCM',
      length: 256,
    },
    true,
    ['encrypt']
  );

  // 3. Generate 96-bit (12-byte) initialization vector
  const iv = cryptoObj.getRandomValues(new Uint8Array(12));

  // 4. Encrypt the plaintext using AES-GCM
  const encodedPlaintext = new TextEncoder().encode(plaintext);
  const encryptedResult = await subtle.encrypt(
    {
      name: 'AES-GCM',
      iv: iv,
      tagLength: 128,
    },
    sessionKey,
    encodedPlaintext
  );

  // Web Crypto AES-GCM outputs ciphertext + 16-byte authentication tag concatenated
  const encryptedBytes = new Uint8Array(encryptedResult);
  const tagLength = 16;
  const ciphertextBytes = encryptedBytes.slice(0, encryptedBytes.length - tagLength);
  const tagBytes = encryptedBytes.slice(encryptedBytes.length - tagLength);

  // 5. Export session key and encrypt it with the server's RSA public key (RSA-OAEP with SHA-256)
  const rawSessionKey = await subtle.exportKey('raw', sessionKey);
  const encryptedSessionKey = await subtle.encrypt(
    {
      name: 'RSA-OAEP',
    },
    serverPublicKey,
    rawSessionKey
  );

  // 6. Return standard EncryptedFieldPayload envelope
  return {
    __encrypted__: true,
    key_id: keyId,
    encrypted_key: arrayBufferToBase64(encryptedSessionKey),
    iv: arrayBufferToBase64(iv),
    ciphertext: arrayBufferToBase64(ciphertextBytes),
    tag: arrayBufferToBase64(tagBytes),
  };
}
