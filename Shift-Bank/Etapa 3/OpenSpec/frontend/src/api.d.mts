export function assertSecureTransport(path: string, protocol: string): void;
export function apiRequest<T = unknown>(url: string, init?: RequestInit, options?: { protocol?: string; fetchImpl?: typeof fetch }): Promise<T>;
