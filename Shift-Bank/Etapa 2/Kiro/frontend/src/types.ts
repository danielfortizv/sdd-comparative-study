// Tipos compartidos de la UI. Los montos siempre son `string` (decimal-string),
// nunca `number`, para preservar la exactitud decimal (Requisito 3.5).

export type AccountKind = "checking" | "savings";

export interface Account {
  name: string; // nombre amigable: "Checking" | "Savings"
  balance: string; // decimal-string
}

export interface AccountsResponse {
  accounts: Account[];
}

export type TransferStatus = "PENDING_MFA" | "COMPLETED" | "FAILED" | "EXPIRED";

export interface CreateTransferRequest {
  from: AccountKind;
  to: AccountKind;
  amount: string; // decimal-string
  description: string;
}

export interface CreateTransferResponse {
  status: TransferStatus;
  mfa_required: boolean;
  reference?: string | null;
  expires_at?: string | null;
}

export interface MfaResponse {
  status: TransferStatus;
}

// Estados de una transferencia ACH (minúsculas, D03). Las internas usan `TransferStatus`
// (MAYÚSCULAS). El historial unificado puede traer cualquiera de los dos conjuntos; por eso
// `HistoryItemStatus` admite ambos (compatibilidad aditiva, Requisito 6/15).
export type AchStatus =
  | "pending_auth"
  | "pending"
  | "settled"
  | "failed"
  | "expired";

export type HistoryItemStatus = TransferStatus | AchStatus;

// Tipo discriminador de una entrada del historial (DD-1): interna o ACH.
export type TransferType = "internal" | "ach";

// Beneficiario tal como lo expone la API: la cuenta solo aparece enmascarada (D05); el routing
// (identificador público de banco) se expone completo (F14).
export interface BeneficiaryMasked {
  name: string;
  bank: string;
  account_masked: string; // "••••" + últimos 4 dígitos
}

export interface TransferHistoryItem {
  type: TransferType;
  date: string;
  // Solo presente en entradas internas (nombres amigables). Opcional para no romper las ACH,
  // que no llevan `direction` sino `beneficiary` (compatibilidad aditiva, UI-1).
  direction?: { from: string; to: string };
  // Solo presente en entradas ACH (beneficiario enmascarado).
  beneficiary?: BeneficiaryMasked;
  amount: string; // decimal-string
  description: string;
  status: HistoryItemStatus;
}

export interface TransfersHistoryResponse {
  transfers: TransferHistoryItem[];
}

export interface ApiError {
  code: string;
  message: string;
}

// ---------------------------------------------------------------------------
// Beneficiarios (Requisitos 1, 2)
// ---------------------------------------------------------------------------

// Beneficiario listado por la API: el `id` es un identificador opaco de referencia (no interno
// expuesto como dato sensible), la cuenta va enmascarada y el routing visible (F14).
export interface Beneficiary extends BeneficiaryMasked {
  id: string;
  routing_number: string;
}

export interface BeneficiariesResponse {
  beneficiaries: Beneficiary[];
}

// Alta de beneficiario: el frontend replica la validación de formato (routing 9 dígitos, cuenta
// 4–17 dígitos) para feedback inmediato (ACH-10), pero la autoridad es el backend.
export interface CreateBeneficiaryRequest {
  name: string;
  bank: string;
  routing_number: string;
  account_number: string;
}

// La creación devuelve el beneficiario ya enmascarado (mismo shape que un ítem de la lista).
export type CreateBeneficiaryResponse = Beneficiary;

export interface DeleteBeneficiaryResponse {
  status: string; // "deleted"
}

// ---------------------------------------------------------------------------
// Transferencias ACH (Requisitos 3, 4, 5)
// ---------------------------------------------------------------------------

// Datos de un beneficiario ad hoc (ACH sin guardar). Montos/validación como en beneficiarios.
export interface AdhocBeneficiary {
  name: string;
  bank: string;
  routing_number: string;
  account_number: string;
}

// Creación de una ACH: usa un beneficiario guardado (`beneficiary_id`) o datos ad hoc (`adhoc`),
// con opción de persistir el ad hoc (`save_adhoc`). Monto como decimal-string.
export interface CreateAchRequest {
  amount: string; // decimal-string
  description?: string;
  from?: AccountKind;
  beneficiary_id?: string;
  adhoc?: AdhocBeneficiary;
  save_adhoc?: boolean;
}

// Respuesta de creación ACH: si el monto es sensible (≥ umbral) → `pending_auth` con
// `mfa_required: true` y `reference`/`expires_at` para confirmar; si no, `pending` ya debitada.
export interface CreateAchResponse {
  status: AchStatus;
  mfa_required: boolean;
  reference?: string | null;
  expires_at?: string | null;
}

// Confirmación de MFA de una ACH sensible (`pending_auth` → `pending` + débito).
export interface AchMfaResponse {
  status: AchStatus;
}

// ---------------------------------------------------------------------------
// Pagos recurrentes (Requisitos 8, 9, 12)
// ---------------------------------------------------------------------------

export type RecurringFrequency = "daily" | "weekly" | "monthly";

export type RecurringStatus = "active" | "paused" | "cancelled";

// Ítem de schedule listado: estado + próxima fecha de vencimiento y datos para mostrarlo.
export interface RecurringSchedule {
  id: string;
  type: TransferType;
  status: RecurringStatus;
  frequency: RecurringFrequency;
  amount: string; // decimal-string
  description: string;
  next_run_at: string; // ISO-8601 UTC
  requires_mfa: boolean;
  authorized: boolean;
}

export interface RecurringResponse {
  recurring: RecurringSchedule[];
}

// Creación de un schedule interno o ACH. Para internos se usa `to`; para ACH, `beneficiary_id`
// o `adhoc`. `start_at` opcional (REC-04). `mfa_code` solo si el monto es sensible (REC-09).
export interface CreateRecurringRequest {
  type: TransferType;
  amount: string; // decimal-string
  frequency: RecurringFrequency;
  from?: AccountKind;
  to?: AccountKind;
  beneficiary_id?: string;
  adhoc?: AdhocBeneficiary;
  description?: string;
  start_at?: string;
  mfa_code?: string;
}

// Respuesta de creación de schedule: estado inicial + próxima fecha + banderas de autorización.
export interface CreateRecurringResponse {
  id: string;
  type: TransferType;
  status: RecurringStatus;
  frequency: RecurringFrequency;
  next_run_at: string;
  requires_mfa: boolean;
  authorized: boolean;
}

// Respuesta de pausar/reanudar/cancelar: id + nuevo estado + próxima fecha recalculada (D06).
export interface RecurringLifecycleResponse {
  id: string;
  status: RecurringStatus;
  next_run_at: string;
}

// ---------------------------------------------------------------------------
// Límites de transferencia dinámicos (Requisitos 13, 14)
// ---------------------------------------------------------------------------

// Lectura de límites: valores vigentes + consumo y disponibilidad del día UTC (LIM-02).
export interface LimitsResponse {
  per_transfer: string; // decimal-string
  daily: string; // decimal-string
  daily_consumed: string; // decimal-string
  daily_remaining: string; // decimal-string
}

// Actualización de límites: ambos opcionales (actualización parcial). Montos decimal-string.
export interface UpdateLimitsRequest {
  per_transfer?: string;
  daily?: string;
}

// La actualización devuelve únicamente los límites vigentes tras aplicar el cambio.
export interface UpdateLimitsResponse {
  per_transfer: string; // decimal-string
  daily: string; // decimal-string
}
