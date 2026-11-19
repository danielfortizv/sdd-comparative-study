const sensitivePrefixes = ['/api/beneficiaries', '/api/ach-transfers', '/api/recurring-schedules', '/api/history'];

export function assertSecureTransport(path, protocol) {
  if (sensitivePrefixes.some(prefix => path.startsWith(prefix)) && protocol !== 'https:') {
    throw new Error('Sensitive banking operations require a secure HTTPS connection.');
  }
}

export async function apiRequest(url, init = {}, { protocol = globalThis.location?.protocol, fetchImpl = globalThis.fetch } = {}) {
  assertSecureTransport(url, protocol);
  const response = await fetchImpl(url, { ...init, headers: { 'Content-Type': 'application/json', ...(init.headers || {}) } });
  const body = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body?.detail || `Request failed (${response.status})`);
  return body;
}
