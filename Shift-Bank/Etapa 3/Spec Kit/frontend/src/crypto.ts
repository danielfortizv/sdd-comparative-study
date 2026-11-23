import { CryptographicEnvelope, PublicKeyResponse } from './types';

let cachedPublicKey: CryptoKey | null = null;

function arrayBufferToBase64(buffer: ArrayBuffer | Uint8Array): string {
  const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}

function pemToArrayBuffer(pem: string): ArrayBuffer {
  const b64 = pem
    .replace(/-----BEGIN [A-Z ]+-----/, '')
    .replace(/-----END [A-Z ]+-----/, '')
    .replace(/[\r\n\s]/g, '');
  const binary = window.atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

export async function fetchAndImportPublicKey(): Promise<CryptoKey> {
  if (cachedPublicKey) {
    return cachedPublicKey;
  }
  const response = await fetch('/api/crypto/public-key');
  if (!response.ok) {
    throw new Error('Failed to retrieve backend cryptographic public key');
  }
  const data: PublicKeyResponse = await response.json();
  const keyBuffer = pemToArrayBuffer(data.public_key);
  cachedPublicKey = await window.crypto.subtle.importKey(
    'spki',
    keyBuffer,
    {
      name: 'RSA-OAEP',
      hash: 'SHA-256',
    },
    false,
    ['encrypt']
  );
  return cachedPublicKey;
}

export async function encryptPayload<T extends object>(payload: T): Promise<CryptographicEnvelope> {
  const rsaPublicKey = await fetchAndImportPublicKey();

  // 1. Generate ephemeral 256-bit AES-GCM symmetric key
  const aesKey = await window.crypto.subtle.generateKey(
    { name: 'AES-GCM', length: 256 },
    true,
    ['encrypt']
  );

  // 2. Generate random 12-byte IV
  const iv = window.crypto.getRandomValues(new Uint8Array(12));

  // 3. Serialize payload and encrypt with AES-GCM
  const encodedPayload = new TextEncoder().encode(JSON.stringify(payload));
  const encryptedBuffer = await window.crypto.subtle.encrypt(
    { name: 'AES-GCM', iv: iv },
    aesKey,
    encodedPayload
  );

  // In Web Crypto, AES-GCM appends the 16-byte tag to the ciphertext buffer
  const encryptedBytes = new Uint8Array(encryptedBuffer);
  const tagLength = 16;
  const ciphertextBytes = encryptedBytes.slice(0, encryptedBytes.length - tagLength);
  const tagBytes = encryptedBytes.slice(encryptedBytes.length - tagLength);

  // 4. Wrap ephemeral AES key with backend RSA-OAEP public key
  const rawAesKey = await window.crypto.subtle.exportKey('raw', aesKey);
  const wrappedKeyBuffer = await window.crypto.subtle.encrypt(
    { name: 'RSA-OAEP' },
    rsaPublicKey,
    rawAesKey
  );

  return {
    encrypted_key: arrayBufferToBase64(wrappedKeyBuffer),
    iv: arrayBufferToBase64(iv),
    ciphertext: arrayBufferToBase64(ciphertextBytes),
    tag: arrayBufferToBase64(tagBytes),
  };
}

export function clearPublicKeyCache(): void {
  cachedPublicKey = null;
}
