// HTTP/JSON API client module. This is the single boundary through which the
// frontend talks to the backend (design: API Client, Requirements 14.3, 14.4).
//
// Typed client methods for each backend endpoint drive the loading/error
// states the UI shows while a request is in flight or after it fails
// (Requirements 12.2, 12.4). Return types faithfully mirror the backend JSON;
// callers derive any UI-local shape (such as SessionState) from these.

import type {
  CheckoutConfirmation,
  CheckoutRequest,
  Credentials,
  Product,
} from "../types";

/** Base URL of the separately-run backend service. */
export const API_BASE_URL = "http://localhost:8000";

// --- Backend response shapes -------------------------------------------------
//
// These interfaces mirror the exact JSON the backend sends. They live here (not
// in src/types.ts) because they are transport-level contracts of this client,
// not shared domain types. Callers map them onto UI state as needed.

/** Session representation returned by `POST /auth/login` and `POST /auth/logout`. */
export interface SessionResponse {
  active: boolean;
  customerId: string | null;
}

/** Account identity returned by a successful `POST /auth/register` (201). */
export interface AccountResponse {
  id: string;
  identifier: string;
}

/**
 * Structured error body a backend endpoint may return on a non-OK status.
 * Every field is optional because different endpoints surface different shapes:
 * - 422 registration: `{ error, message, emptyFields, nonConformingFields }`
 * - 409 registration / 401 login: `{ error, message? }` or `{ error }`
 * - 404 product: `{ error, message, productId }`
 * - 400 checkout: `{ detail: { code, message } }`
 */
export interface ApiErrorDetail {
  error?: string;
  message?: string;
  code?: string;
  productId?: string;
  emptyFields?: string[];
  nonConformingFields?: string[];
}

// --- Error type --------------------------------------------------------------

/**
 * Error raised when an API request fails or returns a non-OK status.
 *
 * Captures the HTTP {@link status} and, when the response carried a JSON body,
 * the structured {@link detail} parsed from it. The UI reads these to show the
 * invalid-data state (R12.1) and the request-failure state (R12.4) with a
 * message describing what happened.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: ApiErrorDetail | null;

  constructor(
    message: string,
    status: number,
    detail: ApiErrorDetail | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

// --- Request plumbing --------------------------------------------------------

/**
 * Normalize the backend's two error-body shapes into a flat {@link ApiErrorDetail}.
 * Most endpoints return the fields at the top level; the checkout endpoint nests
 * them under `detail`. Returns `null` when nothing usable can be extracted.
 */
function extractErrorDetail(body: unknown): ApiErrorDetail | null {
  if (body === null || typeof body !== "object") {
    return null;
  }
  const source = body as Record<string, unknown>;
  // `POST /checkout/confirm` nests the error under `detail: { code, message }`.
  const nested =
    source.detail && typeof source.detail === "object"
      ? (source.detail as Record<string, unknown>)
      : source;

  const detail: ApiErrorDetail = {};
  if (typeof nested.error === "string") detail.error = nested.error;
  if (typeof nested.message === "string") detail.message = nested.message;
  if (typeof nested.code === "string") detail.code = nested.code;
  if (typeof nested.productId === "string") detail.productId = nested.productId;
  if (Array.isArray(nested.emptyFields)) {
    detail.emptyFields = nested.emptyFields.filter(
      (field): field is string => typeof field === "string",
    );
  }
  if (Array.isArray(nested.nonConformingFields)) {
    detail.nonConformingFields = nested.nonConformingFields.filter(
      (field): field is string => typeof field === "string",
    );
  }

  return Object.keys(detail).length > 0 ? detail : null;
}

/** Pick the most descriptive message available for an {@link ApiError}. */
function messageFromDetail(
  detail: ApiErrorDetail | null,
  fallback: string,
): string {
  if (detail?.message) return detail.message;
  if (detail?.error) return detail.error;
  return fallback;
}

/**
 * Perform a JSON request against the backend and return the parsed body.
 *
 * Throws {@link ApiError} on a non-OK response or a transport failure so callers
 * can surface the invalid-data (R12.1) or request-failure (R12.4) state. Error
 * bodies are parsed defensively: a non-OK response is not guaranteed to carry
 * JSON, so a parse failure degrades to a status-only {@link ApiError}.
 */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    // Network/transport failure: no HTTP status is available.
    throw new ApiError("The request could not be completed.", 0);
  }

  if (!response.ok) {
    let detail: ApiErrorDetail | null = null;
    try {
      detail = extractErrorDetail(await response.json());
    } catch {
      // Body was absent or not valid JSON; keep a status-only error.
      detail = null;
    }
    throw new ApiError(
      messageFromDetail(detail, `The request to ${path} failed.`),
      response.status,
      detail,
    );
  }

  return (await response.json()) as T;
}

// --- Typed client ------------------------------------------------------------

/**
 * Typed client for the six backend endpoints. Each method returns the backend's
 * JSON shape verbatim; `register`/`login`/`logout` return the account identity
 * or session representation the backend actually sends, and callers derive the
 * UI's `SessionState` from them.
 */
export const apiClient = {
  listProducts(): Promise<Product[]> {
    return request<Product[]>("/products");
  },

  getProduct(id: string): Promise<Product> {
    return request<Product>(`/products/${encodeURIComponent(id)}`);
  },

  register(credentials: Credentials): Promise<AccountResponse> {
    return request<AccountResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(credentials),
    });
  },

  login(credentials: Credentials): Promise<SessionResponse> {
    return request<SessionResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(credentials),
    });
  },

  logout(): Promise<SessionResponse> {
    return request<SessionResponse>("/auth/logout", { method: "POST" });
  },

  confirmCheckout(payload: CheckoutRequest): Promise<CheckoutConfirmation> {
    return request<CheckoutConfirmation>("/checkout/confirm", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};

export type ApiClient = typeof apiClient;
