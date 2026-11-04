/**
 * Typed API contract for the Evaluate_Endpoint (`POST /api/v1/evaluate`).
 *
 * These types mirror the backend's Pydantic schemas and the JSON contract
 * documented in the design's API Contract section. The response is modeled as
 * a discriminated union whose two members are distinguished purely by the
 * presence of a string `result` field (success) or a string `error` field
 * (error) — success and error payloads are mutually exclusive.
 *
 * Requirements: 13.1, 13.2, 13.3, 13.4, 13.5
 */

/**
 * Selectable angle unit for trigonometric evaluation. Modeled as a restricted
 * literal union that mirrors the backend's `Literal["radians", "degrees"]`, so
 * only these two values are representable in the typed contract (Requirement
 * 24.6).
 */
export type AngleMode = "radians" | "degrees";

/**
 * Request payload sent to the Evaluate_Endpoint (Requirements 13.1, 24.6). The
 * `angleMode` field selects the angle unit for trigonometric evaluation. The
 * API client serializes it to the backend's snake_case `angle_mode` field; the
 * serialization itself lives in `client.ts` — this is purely the typed contract.
 */
export interface EvaluateRequest {
  expression: string;
  angleMode: AngleMode;
}

/** Successful evaluation response (Requirement 13.2). */
export interface EvaluateSuccess {
  result: string;
}

/** Structured error response (Requirement 13.3). */
export interface ErrorResponse {
  error: string;
}

/**
 * The full set of shapes the endpoint is contracted to return. A conforming
 * response is exactly one of these two members (Requirement 5.5).
 */
export type EvaluateResponse = EvaluateSuccess | ErrorResponse;

/**
 * The Memory_Register value. Held as a decimal string rather than a JavaScript
 * number so the backend's exact-decimal precision is preserved verbatim with no
 * float coercion (Requirement 24.6).
 */
export interface MemoryState {
  value: string;
}

/**
 * A single Calculation_History entry pairing a submitted expression with the
 * backend result string (Requirement 24.6).
 */
export interface HistoryEntry {
  expression: string;
  result: string;
}

/**
 * The session Calculation_History: a read-only list of {@link HistoryEntry}
 * records ordered newest-first and capped at 100 entries. The ordering and the
 * cap are enforced by the history reducer (task 32); this type only expresses
 * the immutable shape (Requirement 24.6).
 */
export type CalculationHistory = readonly HistoryEntry[];

/**
 * Narrows an arbitrary value to a record so individual fields can be inspected
 * without resorting to the `any` type (Requirement 13.4).
 */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/**
 * Runtime type guard for {@link EvaluateSuccess}. Validates that the value is
 * an object carrying a string `result` field (Requirement 13.5). A value that
 * also carries an `error` field is not treated as a success, keeping the
 * success/error distinction unambiguous (Requirement 5.5).
 */
export function isSuccess(r: unknown): r is EvaluateSuccess {
  return isRecord(r) && typeof r.result === "string" && !("error" in r);
}

/**
 * Runtime type guard for {@link ErrorResponse}. Validates that the value is an
 * object carrying a string `error` field (Requirement 13.5). A value that also
 * carries a `result` field is not treated as an error, keeping the
 * success/error distinction unambiguous (Requirement 5.5).
 */
export function isError(r: unknown): r is ErrorResponse {
  return isRecord(r) && typeof r.error === "string" && !("result" in r);
}
