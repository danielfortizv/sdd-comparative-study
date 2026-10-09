/**
 * Typed API client for the Evaluate_Endpoint (`POST /api/v1/evaluate`).
 *
 * The client owns the transport concern only: it constructs a typed
 * {@link EvaluateRequest}, sends it to the backend, and normalizes every
 * possible outcome into a single discriminated {@link EvaluateResult} union so
 * callers (hooks/components) never have to reason about HTTP status codes,
 * JSON parsing, or malformed payloads themselves.
 *
 * The frontend performs no arithmetic: a `result` is only ever produced by a
 * successful backend response (Requirement 14.3). Any transport failure or
 * non-conforming payload is surfaced as an error (Requirements 13.5, 14.4).
 *
 * Requirements: 13.4, 13.5, 14.3, 14.4
 */

import { isError, isSuccess, type EvaluateRequest } from "./types";

/** Endpoint path. Relative so the Vite dev server proxies `/api` to the backend. */
const EVALUATE_ENDPOINT = "/api/v1/evaluate";

/** Message shown when a response conforms to neither typed shape (Requirement 13.5). */
const NON_CONFORMING_MESSAGE = "The evaluation service returned an unexpected response.";

/** Message shown when the backend cannot be reached (Requirement 14.4). */
const SERVICE_UNAVAILABLE_MESSAGE = "The evaluation service is unavailable.";

/**
 * Normalized outcome of an evaluation request. This is the single shape callers
 * consume: on success `ok` is `true` and `result` carries the backend's exact
 * decimal string; on any failure `ok` is `false` and `error` carries a
 * human-readable message. The `ok` boolean is the discriminant, so TypeScript
 * narrows `result`/`error` automatically in each branch.
 */
export type EvaluateResult =
  | { ok: true; result: string }
  | { ok: false; error: string };

/**
 * Evaluate an arithmetic expression via the backend.
 *
 * Builds a typed {@link EvaluateRequest} (no `any`), POSTs it as JSON to the
 * Evaluate_Endpoint, and returns a normalized {@link EvaluateResult}:
 *
 * - A body narrowed by {@link isSuccess} → `{ ok: true, result }`.
 * - A body narrowed by {@link isError} → `{ ok: false, error }` (covers the
 *   backend's 4xx error responses, which carry an `error` field).
 * - A body matching neither guard → `{ ok: false }` with a generic message
 *   (Requirement 13.5).
 * - A network/transport failure (fetch rejects) → `{ ok: false }` with the
 *   service-unavailable message, and never a locally computed result
 *   (Requirement 14.4).
 */
export async function evaluateExpression(expression: string): Promise<EvaluateResult> {
  const requestBody: EvaluateRequest = { expression };

  let response: Response;
  try {
    response = await fetch(EVALUATE_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
    });
  } catch {
    // The backend is unreachable (offline, DNS/connection failure, CORS, etc.).
    return { ok: false, error: SERVICE_UNAVAILABLE_MESSAGE };
  }

  // Parse the body defensively: a non-JSON or empty body is itself a
  // non-conforming response and is treated as an error (Requirement 13.5).
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    return { ok: false, error: NON_CONFORMING_MESSAGE };
  }

  if (isSuccess(payload)) {
    return { ok: true, result: payload.result };
  }

  if (isError(payload)) {
    return { ok: false, error: payload.error };
  }

  // Conforms to neither the success nor the error shape (Requirement 13.5).
  return { ok: false, error: NON_CONFORMING_MESSAGE };
}
