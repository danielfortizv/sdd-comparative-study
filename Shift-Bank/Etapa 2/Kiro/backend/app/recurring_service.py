"""Reglas de negocio de pagos recurrentes (Etapa 2, Fase E).

Alcance de las Tareas 27–28 (creación/persistencia + autorización MFA en creación):
- Crear un schedule interno o ACH con origen/destino/monto/frecuencia válidos.
- Estado inicial `active` (REC-03, Req. 8.3).
- Cálculo de la primera fecha de vencimiento (REC-04, Req. 8.4/8.5):
  * fecha de inicio futura válida → esa fecha es `next_run_at`;
  * fecha omitida → `next_run_at` = creación + un intervalo completo (nunca inmediata).
- Snapshot de beneficiario para los schedules ACH (REC-11, Req. 8.7), de modo que el schedule
  siga siendo ejecutable aunque el beneficiario guardado se elimine después.
- Autorización MFA en creación de schedules sensibles (Tarea 28, Req. 8.6, REC-09, D04): si el
  monto ≥ umbral, la creación EXIGE MFA (código heredado de la Etapa 1); al superarla el
  schedule se persiste con `authorized=1`. Si la MFA es obligatoria y falta o es incorrecta, la
  creación se RECHAZA (no se persiste un schedule sensible no autorizado). Las ejecuciones
  automáticas NO piden MFA interactiva (Req. 11.4, D02); la autorización se concede una vez en
  creación.

Controles de ciclo de vida (Tarea 29, Req. 9, REC-06/07/08, D06, A18):
- Pausar (`active→paused`), reanudar (`paused→active`) y cancelar (`→cancelled`, terminal).
- Reanudación SIN catch-up (D06, Req. 9.6): al reanudar se descartan las ocurrencias vencidas
  durante la pausa y `next_run_at` se recalcula desde el instante de reanudación (reanudación +
  un intervalo completo), sin pagos duplicados ni débitos acumulados.
- `cancelled` es terminal (Req. 9.7): reanudar/modificar un `cancelled` (u otras transiciones
  ilegales, p. ej. pausar un `cancelled`) se rechazan con `INVALID_STATE_TRANSITION`, sin mutar
  el estado. Las transiciones NO piden MFA interactiva (la autorización se concede en creación).

Ejecución durable y atómica de ocurrencias (Tarea 30, Req. 10.3/10.4/11.1/11.3, DD-7/F10, D07):
- `process_due(conn, now)` es una función PURA (determinista dado `(conn, now)`, sin lecturas de
  reloj de pared ni asincronía): procesa cada schedule elegible (`active`, `authorized=1`,
  `next_run_at <= now`), cada uno en SU PROPIA `financial_transaction` (`BEGIN IMMEDIATE`), de
  modo que el fallo/rollback de una ocurrencia no aborta las demás.
- Por ocurrencia, dentro de UNA transacción: (1) `INSERT` en `schedule_execution(schedule_id,
  due_at)` —la `UNIQUE` bloquea duplicados; (2) revalidar fondos/límites; (3) crear el
  movimiento (interno COMPLETED, o ACH `pending` + débito); (4) avanzar `next_run_at`. Crash
  antes de COMMIT ⇒ ROLLBACK total; tras COMMIT, el reintento falla el `INSERT` (idempotencia
  durable, D07).
- Fallo de negocio en la revalidación (fondos/límite): se registra la ocurrencia con
  `outcome='failed'` SIN debitar y se avanza `next_run_at` (REC-10, Req. 11.2), de modo que el
  schedule no quede atascado. El disparo autónomo (scheduler) y los endpoints son tareas
  posteriores.

Fuera de alcance (tareas posteriores; NO se implementan aquí):
- Scheduler de fondo (Tarea 32) y endpoints (Tarea 33).

Convenciones heredadas: dinero en centavos enteros; fechas ISO-8601 UTC (`clock.iso`); sin ORM;
SQL puro vía `repository`. Reutiliza `beneficiaries` (validación/snapshot) y `ach_repository`
(resolución de beneficiario guardado con propiedad del cliente, ACH-02).

_Requisitos: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 11.4_ · _Contrato: REC-01..04, REC-09, REC-11;
A15, A16_
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from . import ach_repository, beneficiaries, clock, limit_service, repository
from .config import MFA_CODE, MFA_THRESHOLD, RECURRENCE_INTERVAL_DAYS
from .money import InvalidAmountError, decimal_to_cents, parse_amount
from .txn import financial_transaction

# Tipos de destino interno válidos (coinciden con las cuentas sembradas de la Etapa 1).
_INTERNAL_KINDS = ("checking", "savings")

# Umbral MFA heredado expresado en centavos (>= 1.000.000 COP). Marca la sensibilidad del
# schedule: un monto a partir de este valor exige MFA en creación (Tarea 28, Req. 8.6).
_MFA_THRESHOLD_CENTS = decimal_to_cents(MFA_THRESHOLD)


class RecurringError(Exception):
    """Error de dominio de pagos recurrentes con un `code` estable para el mapeo a HTTP."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ScheduleCreateResult:
    id: str
    type: str
    status: str
    frequency: str
    next_run_at: str
    requires_mfa: bool
    authorized: bool


@dataclass
class ScheduleLifecycleResult:
    """Resultado de una transición de ciclo de vida (pausar/reanudar/cancelar)."""

    id: str
    status: str
    next_run_at: str


def _customer_id(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT id FROM customer LIMIT 1").fetchone()
    if row is None:
        raise RecurringError("NOT_FOUND", "Cliente no encontrado")
    return row["id"]


def _interval(frequency: str) -> timedelta:
    """Devuelve el intervalo de recurrencia (REC-02). Lanza RecurringError si es inválido."""
    days = RECURRENCE_INTERVAL_DAYS.get(frequency)
    if days is None:
        raise RecurringError(
            "INVALID_FREQUENCY",
            "La frecuencia debe ser 'daily', 'weekly' o 'monthly'",
        )
    return timedelta(days=days)


def _parse_amount_cents(amount_raw: str) -> int:
    """Valida y convierte el monto (positivo, <=2 decimales) a centavos enteros (Req. 8.1)."""
    try:
        amount = parse_amount(amount_raw)
    except InvalidAmountError as exc:
        raise RecurringError("INVALID_AMOUNT", str(exc)) from exc
    if amount <= 0:
        raise RecurringError("NON_POSITIVE_AMOUNT", "El monto debe ser mayor que cero")
    try:
        return decimal_to_cents(amount)
    except InvalidAmountError as exc:
        raise RecurringError("INVALID_AMOUNT", str(exc)) from exc


def _compute_first_run(
    *, now: datetime, interval: timedelta, start_at_raw: str | None
) -> datetime:
    """Calcula la primera fecha de vencimiento (REC-04).

    - Si se proporciona una fecha de inicio **futura** válida, esa fecha es `next_run_at`
      (Req. 8.4). Una fecha no futura se rechaza.
    - Si se omite, `next_run_at` = `now` + un intervalo completo, nunca inmediata (Req. 8.5).
    """
    if start_at_raw is None:
        return now + interval
    try:
        start = clock.parse_iso(start_at_raw)
    except (ValueError, TypeError) as exc:
        raise RecurringError(
            "INVALID_START_DATE",
            "La fecha de inicio debe ser ISO-8601 UTC (p. ej. 2026-02-01T00:00:00Z)",
        ) from exc
    if start <= now:
        raise RecurringError(
            "INVALID_START_DATE", "La fecha de inicio debe ser futura")
    return start


def _resolve_internal_destination(from_kind: str, to_kind: str | None) -> str:
    """Valida origen y destino internos (ambos cuentas conocidas y distintas)."""
    if from_kind not in _INTERNAL_KINDS:
        raise RecurringError("INVALID_SOURCE", "La cuenta de origen no es válida")
    if to_kind not in _INTERNAL_KINDS:
        raise RecurringError("INVALID_DESTINATION", "La cuenta de destino no es válida")
    if to_kind == from_kind:
        raise RecurringError(
            "INVALID_DESTINATION", "El origen y el destino no pueden ser la misma cuenta")
    return to_kind


def _resolve_ach_snapshot(
    conn: sqlite3.Connection,
    customer_id: str,
    *,
    beneficiary_id: str | None,
    adhoc: dict | None,
) -> tuple[str | None, dict]:
    """Resuelve el beneficiario ACH (guardado con propiedad, o ad hoc con formato válido).

    Devuelve `(beneficiary_id | None, snapshot)`. El snapshot se persiste con el schedule para
    conservar los datos de destino aunque el beneficiario guardado se elimine después (REC-11).
    """
    if beneficiary_id:
        row = ach_repository.get_beneficiary(conn, customer_id, beneficiary_id)
        if row is None:
            raise RecurringError("NOT_FOUND", "Beneficiario no encontrado")
        snapshot = {
            "name": row["name"],
            "bank": row["bank"],
            "routing_number": row["routing_number"],
            "account_number": row["account_number"],
        }
        return beneficiary_id, snapshot
    if adhoc:
        try:
            beneficiaries.validate_fields(
                name=adhoc.get("name", ""),
                bank=adhoc.get("bank", ""),
                routing_number=adhoc.get("routing_number", ""),
                account_number=adhoc.get("account_number", ""),
            )
        except beneficiaries.BeneficiaryError as exc:
            raise RecurringError(exc.code, exc.message) from exc
        snapshot = {
            "name": adhoc["name"],
            "bank": adhoc["bank"],
            "routing_number": adhoc["routing_number"],
            "account_number": adhoc["account_number"],
        }
        return None, snapshot
    raise RecurringError(
        "INVALID_BENEFICIARY", "Un schedule ACH requiere un beneficiario guardado o ad hoc")


def create_schedule(
    conn: sqlite3.Connection,
    *,
    type: str,
    amount_raw: str,
    frequency: str,
    from_kind: str = "checking",
    to_kind: str | None = None,
    beneficiary_id: str | None = None,
    adhoc: dict | None = None,
    description: str = "",
    start_at: str | None = None,
    mfa_code: str | None = None,
    now: datetime | None = None,
) -> ScheduleCreateResult:
    """Crea y persiste un schedule interno o ACH (Tareas 27–28).

    Valida origen/destino/monto/frecuencia; fija estado inicial `active`; calcula la primera
    fecha de vencimiento (fecha futura dada o creación + un intervalo completo); guarda el
    snapshot del beneficiario para ACH (REC-11).

    Autorización MFA en creación (Tarea 28, Req. 8.6, REC-09, D04): si el monto ≥ umbral, el
    schedule es sensible y la creación EXIGE la MFA heredada (`mfa_code` == código fijo). Con la
    MFA correcta se persiste `authorized=1`; si falta o es incorrecta se rechaza la creación
    (`MFA_REQUIRED` / `INVALID_MFA_CODE`) y NO se persiste un schedule sensible no autorizado.
    Los schedules no sensibles se crean directamente con `authorized=1` (sin MFA). La
    autorización se concede UNA sola vez: las ejecuciones automáticas no piden MFA (Req. 11.4).
    """
    if now is None:
        now = clock.system_clock.now_utc()

    if type not in ("internal", "ach"):
        raise RecurringError("INVALID_TYPE", "El tipo debe ser 'internal' o 'ach'")

    customer_id = _customer_id(conn)
    amount_cents = _parse_amount_cents(amount_raw)
    interval = _interval(frequency)

    if from_kind not in _INTERNAL_KINDS:
        raise RecurringError("INVALID_SOURCE", "La cuenta de origen no es válida")

    resolved_to_kind: str | None = None
    resolved_bid: str | None = None
    snapshot_json: str | None = None

    if type == "internal":
        resolved_to_kind = _resolve_internal_destination(from_kind, to_kind)
    else:  # ach
        resolved_bid, snapshot = _resolve_ach_snapshot(
            conn, customer_id, beneficiary_id=beneficiary_id, adhoc=adhoc)
        snapshot_json = json.dumps(snapshot)

    next_run_at = _compute_first_run(
        now=now, interval=interval, start_at_raw=start_at)

    # Sensibilidad (Req. 8.6): a partir del umbral, la creación exige MFA. Autorización MFA en
    # creación (Tarea 28, REC-09, D04): se reutiliza la MFA heredada (mismo código fijo y mismo
    # código de error `INVALID_MFA_CODE` que las transferencias/ACH de la Etapa 1/2). Un
    # schedule sensible solo se persiste tras superar la MFA, con `authorized=1`; de lo
    # contrario NO se persiste (no queda un schedule sensible no autorizado y, por tanto, no
    # ejecutable). Las ejecuciones automáticas no vuelven a pedir MFA (Req. 11.4, D02): la
    # autorización se concede aquí, una sola vez.
    requires_mfa = amount_cents >= _MFA_THRESHOLD_CENTS
    if requires_mfa:
        if mfa_code is None:
            raise RecurringError(
                "MFA_REQUIRED",
                "Un schedule sensible (monto ≥ umbral) requiere autorización MFA al crearse",
            )
        if mfa_code != MFA_CODE:
            raise RecurringError("INVALID_MFA_CODE", "Código MFA incorrecto")

    schedule = repository.create_schedule(
        conn,
        customer_id=customer_id,
        type=type,
        from_kind=from_kind,
        to_kind=resolved_to_kind,
        beneficiary_id=resolved_bid,
        beneficiary_snapshot=snapshot_json,
        amount_cents=amount_cents,
        description=description,
        frequency=frequency,
        status="active",
        requires_mfa=requires_mfa,
        authorized=True,  # no sensible: autorizado directo; sensible: MFA ya superada arriba
        next_run_at=clock.iso(next_run_at),
        created_at=clock.iso(now),
    )

    return ScheduleCreateResult(
        id=schedule.id,
        type=schedule.type,
        status=schedule.status,
        frequency=schedule.frequency,
        next_run_at=schedule.next_run_at,
        requires_mfa=bool(schedule.requires_mfa),
        authorized=bool(schedule.authorized),
    )


# --- Controles de ciclo de vida (Tarea 29, Req. 9, REC-06/07/08, D06, A18) ----
#
# Pausar / reanudar / cancelar. Son operaciones de configuración (no mueven saldos): validan la
# propiedad del cliente y la legalidad de la transición y persisten el nuevo estado con su propio
# commit (vía `repository.update_schedule_status`). No piden MFA interactiva (la autorización
# sensible se concede una sola vez en creación, Req. 11.4). La reanudación recalcula `next_run_at`
# desde el instante de reanudación (D06, sin catch-up).


def _get_owned_schedule(
    conn: sqlite3.Connection, schedule_id: str
) -> repository.Schedule:
    """Carga un schedule asegurando la propiedad del cliente.

    Lanza `NOT_FOUND` si no existe o no pertenece al cliente (misma convención que el resto del
    servicio), de modo que un schedule ajeno es indistinguible de uno inexistente.
    """
    customer_id = _customer_id(conn)
    schedule = repository.get_schedule(conn, schedule_id)
    if schedule is None or schedule.customer_id != customer_id:
        raise RecurringError("NOT_FOUND", "Schedule no encontrado")
    return schedule


def pause_schedule(
    conn: sqlite3.Connection, schedule_id: str
) -> ScheduleLifecycleResult:
    """Pausa un schedule `active` (`active → paused`, REC-06, Req. 9.1).

    Un `paused` deja de ser elegible para ejecución (Req. 9.5). Pausar algo que no está `active`
    (ya `paused` o `cancelled`, terminal) es una transición ilegal y se rechaza con
    `INVALID_STATE_TRANSITION` sin mutar el estado (Req. 9.4/9.7).
    """
    schedule = _get_owned_schedule(conn, schedule_id)
    if schedule.status != "active":
        raise RecurringError(
            "INVALID_STATE_TRANSITION",
            f"Solo se puede pausar un schedule 'active' (estado actual: '{schedule.status}')",
        )
    updated = repository.update_schedule_status(conn, schedule_id, "paused")
    return ScheduleLifecycleResult(
        id=updated.id, status=updated.status, next_run_at=updated.next_run_at)


def resume_schedule(
    conn: sqlite3.Connection,
    schedule_id: str,
    *,
    now: datetime | None = None,
) -> ScheduleLifecycleResult:
    """Reanuda un schedule `paused` (`paused → active`) sin catch-up (D06, REC-06/07, Req. 9.2/9.6).

    Al reanudar se **saltan** todas las ocurrencias cuyo vencimiento pasó durante la pausa (no se
    ejecutan retroactivamente) y `next_run_at` se **recalcula desde el instante de reanudación**:
    `now + un intervalo completo` según la frecuencia configurada (1/7/30 días). No se producen
    pagos duplicados ni débitos acumulados inmediatos (D06, A18).

    Reanudar algo que no está `paused` es ilegal: un `cancelled` es terminal y no reanudable
    (Req. 9.4/9.7), y un `active` ya está en ejecución; ambos se rechazan con
    `INVALID_STATE_TRANSITION` sin mutar el estado.
    """
    if now is None:
        now = clock.system_clock.now_utc()

    schedule = _get_owned_schedule(conn, schedule_id)
    if schedule.status != "paused":
        raise RecurringError(
            "INVALID_STATE_TRANSITION",
            f"Solo se puede reanudar un schedule 'paused' (estado actual: '{schedule.status}')",
        )

    interval = _interval(schedule.frequency)
    next_run_at = clock.iso(now + interval)  # desde la reanudación, sin catch-up (D06)
    updated = repository.update_schedule_status(
        conn, schedule_id, "active", next_run_at=next_run_at)
    return ScheduleLifecycleResult(
        id=updated.id, status=updated.status, next_run_at=updated.next_run_at)


def cancel_schedule(
    conn: sqlite3.Connection, schedule_id: str
) -> ScheduleLifecycleResult:
    """Cancela un schedule (`active`/`paused → cancelled`, terminal; REC-06/07, Req. 9.3/9.7).

    `cancelled` es un estado terminal: no vuelve a ejecutarse ni puede reanudarse (Req. 9.5/9.7).
    Cancelar un schedule ya `cancelled` es una transición ilegal y se rechaza con
    `INVALID_STATE_TRANSITION` sin mutar el estado (la cancelación no se revierte, Req. 9.4).
    """
    schedule = _get_owned_schedule(conn, schedule_id)
    if schedule.status == "cancelled":
        raise RecurringError(
            "INVALID_STATE_TRANSITION",
            "Un schedule 'cancelled' es terminal y no admite más transiciones",
        )
    updated = repository.update_schedule_status(conn, schedule_id, "cancelled")
    return ScheduleLifecycleResult(
        id=updated.id, status=updated.status, next_run_at=updated.next_run_at)


# --- Ejecución durable y atómica de ocurrencias (Tarea 30, DD-7/F10, D07) -----
#
# `process_due` recorre los schedules elegibles y ejecuta cada ocurrencia vencida dentro de UNA
# transacción financiera (`BEGIN IMMEDIATE … COMMIT`), con idempotencia durable vía
# `schedule_execution UNIQUE(schedule_id, due_at)`. Es PURA: determinista dado `(conn, now)`, sin
# lecturas de reloj de pared ni asincronía; el disparo temporal lo aporta el scheduler (Tarea 32).


@dataclass
class OccurrenceOutcome:
    """Resultado de intentar ejecutar UNA ocurrencia de un schedule."""

    schedule_id: str
    due_at: str
    # 'executed'   → movimiento creado + débito aplicado + fecha avanzada (COMMIT).
    # 'failed'     → fondos/límite insuficientes: registrada sin débito + fecha avanzada (REC-10).
    # 'skipped'    → la ocurrencia ya estaba registrada (UNIQUE): sin efecto (idempotencia).
    status: str
    transfer_id: str | None = None


@dataclass
class ProcessDueSummary:
    """Resumen estructurado de una corrida de `process_due` (útil para pruebas y Tarea 32)."""

    executed: int = 0
    failed: int = 0
    skipped: int = 0
    outcomes: list[OccurrenceOutcome] = field(default_factory=list)


def _execute_internal_in_tx(
    conn: sqlite3.Connection,
    schedule: repository.Schedule,
    *,
    now_iso: str,
    transfer_id: str,
) -> None:
    """Crea el movimiento interno COMPLETED + débito/crédito SIN gestionar la transacción.

    Reutiliza la semántica interna de la Etapa 1/2 (`apply_transfer_in_tx` hace el
    débito+crédito y marca COMPLETED). La fila se inserta con `type='internal'` y el
    `schedule_id` que la originó.
    """
    repository.create_internal_transfer_no_commit(
        conn,
        transfer_id=transfer_id,
        from_kind=schedule.from_kind,
        to_kind=schedule.to_kind or "",
        amount_cents=schedule.amount_cents,
        description=schedule.description,
        status="pending",  # transitorio; apply_transfer_in_tx lo deja en COMPLETED
        created_at=now_iso,
        completed_at=None,
        schedule_id=schedule.id,
    )
    repository.apply_transfer_in_tx(
        conn,
        transfer_id=transfer_id,
        from_kind=schedule.from_kind,
        to_kind=schedule.to_kind or "",
        amount_cents=schedule.amount_cents,
        completed_at=now_iso,
    )


def _execute_ach_in_tx(
    conn: sqlite3.Connection,
    schedule: repository.Schedule,
    *,
    now_iso: str,
    transfer_id: str,
) -> None:
    """Crea la ACH `pending` + débito inmediato SIN gestionar la transacción (Req. 11.3).

    Aplica el mismo ciclo de vida ACH que la ruta interactiva (`pending` con débito inmediato;
    settlement/fallo quedan para el barrido del scheduler). El `beneficiary_snapshot` del
    schedule se reutiliza como snapshot de la transferencia (REC-11).
    """
    ach_repository.create_ach_no_commit(
        conn,
        transfer_id=transfer_id,
        reference=uuid.uuid4().hex,
        from_kind=schedule.from_kind,
        amount_cents=schedule.amount_cents,
        description=schedule.description,
        status="pending",
        requires_mfa=False,
        created_at=now_iso,
        expires_at=None,
        beneficiary_id=schedule.beneficiary_id,
        beneficiary_snapshot=schedule.beneficiary_snapshot or "{}",
        schedule_id=schedule.id,
    )
    ach_repository.debit_source_no_commit(
        conn, from_kind=schedule.from_kind, amount_cents=schedule.amount_cents)


def _revalidate_funds_and_limits(
    conn: sqlite3.Connection, schedule: repository.Schedule, now: datetime
) -> None:
    """Revalida fondos y límites vigentes en el instante de ejecución (Req. 11.1, LIM-08).

    Reutiliza el MISMO servicio de límites que las rutas interactivas (sin duplicar umbrales).
    Lanza `RecurringError` con un `code` de negocio si la ocurrencia no puede ejecutarse; el
    llamador lo traduce a `outcome='failed'` (sin débito, REC-10).
    """
    src = conn.execute(
        "SELECT balance_cents FROM account WHERE kind = ?", (schedule.from_kind,)).fetchone()
    if src is None or schedule.amount_cents > src["balance_cents"]:
        raise RecurringError("INSUFFICIENT_FUNDS", "Fondos insuficientes en la cuenta de origen")
    try:
        limit_service.check(conn, schedule.amount_cents, now)
    except limit_service.LimitError as exc:
        raise RecurringError(exc.code, exc.message) from exc


def _process_one(
    conn: sqlite3.Connection, schedule: repository.Schedule, now: datetime
) -> OccurrenceOutcome:
    """Ejecuta UNA ocurrencia vencida del schedule dentro de UNA transacción (F10).

    Pasos (todos en la misma `financial_transaction`):
      1. `INSERT` en `schedule_execution(schedule_id, due_at)` — la `UNIQUE(schedule_id, due_at)`
         rechaza una ocurrencia ya procesada (reintento, tick solapado, re-ejecución tras crash
         con la fecha aún sin avanzar): el `INSERT` lanza `IntegrityError` → se omite sin efecto.
      2. Revalidar fondos/límites (Req. 11.1).
      3a. Si pasa: crear el movimiento (interno COMPLETED o ACH `pending`+débito) y avanzar
          `next_run_at` → `outcome='executed'`.
      3b. Si falla por fondos/límite: registrar `outcome='failed'` SIN débito y avanzar
          `next_run_at` (REC-10, Req. 11.2) para que el schedule no quede atascado.

    `due_at` es la identidad de la ocurrencia: el `next_run_at` ORIGINAL del schedule (el
    vencimiento), estable entre reintentos — nunca `now`.
    """
    due_at = schedule.next_run_at  # identidad de la ocurrencia (vencimiento original)
    now_iso = clock.iso(now)
    interval = _interval(schedule.frequency)
    next_run_at = clock.iso(clock.parse_iso(due_at) + interval)

    # Primera decisión (fuera de la transacción financiera, sin mutar nada): ¿pasa la
    # revalidación? Determina el `outcome` y si hay movimiento. La inserción de la fila de
    # ejecución va SIEMPRE primero dentro de la transacción para que la UNIQUE sea la guarda de
    # idempotencia tanto en éxito como en fallo.
    execution_id = str(uuid.uuid4())
    business_ok = False
    transfer_id: str | None = None
    try:
        with financial_transaction(conn):
            # (1) Guarda de idempotencia durable PRIMERO: la fila de ejecución se inserta con
            # `transfer_id=NULL`. Si la ocurrencia ya estaba registrada (reintento, tick
            # solapado, re-ejecución tras crash con la fecha sin avanzar), la
            # `UNIQUE(schedule_id, due_at)` hace fallar este INSERT y se omite, sin efecto.
            # Se inserta antes de crear el movimiento para respetar la FK `transfer_id →
            # transfer.id`: el enlace se hace al final, cuando el movimiento ya existe.
            try:
                _revalidate_funds_and_limits(conn, schedule, now)
                business_ok = True
            except RecurringError:
                business_ok = False

            outcome = "executed" if business_ok else "failed"
            repository.insert_schedule_execution_no_commit(
                conn,
                execution_id=execution_id,
                schedule_id=schedule.id,
                due_at=due_at,
                outcome=outcome,
                transfer_id=None,
                created_at=now_iso,
            )

            if business_ok:
                # (3a) Crear el movimiento + débito según el tipo, en la misma transacción, y
                # enlazarlo con la fila de ejecución.
                transfer_id = str(uuid.uuid4())
                if schedule.type == "internal":
                    _execute_internal_in_tx(
                        conn, schedule, now_iso=now_iso, transfer_id=transfer_id)
                else:  # ach
                    _execute_ach_in_tx(
                        conn, schedule, now_iso=now_iso, transfer_id=transfer_id)
                repository.set_execution_transfer_id_no_commit(
                    conn, execution_id, transfer_id)

            # (4) Avanzar `next_run_at` en AMBOS casos (ejecutado o fallido: REC-10/Req. 11.2),
            # dentro de la misma transacción para que nada quede a medias.
            repository.advance_schedule_next_run_in_tx(conn, schedule.id, next_run_at)
    except sqlite3.IntegrityError as exc:
        # Solo la colisión de `UNIQUE(schedule_id, due_at)` significa "ocurrencia ya procesada"
        # (idempotencia durable). Cualquier otra violación de integridad es un error real y debe
        # propagarse (no enmascararla como 'skipped'). ROLLBACK automático por el context manager.
        if "schedule_execution" in str(exc) or "schedule_id" in str(exc):
            return OccurrenceOutcome(
                schedule_id=schedule.id, due_at=due_at, status="skipped")
        raise

    status = "executed" if business_ok else "failed"
    return OccurrenceOutcome(
        schedule_id=schedule.id, due_at=due_at, status=status,
        transfer_id=transfer_id if business_ok else None)


def process_due(conn: sqlite3.Connection, now: datetime) -> ProcessDueSummary:
    """Procesa todas las ocurrencias vencidas de forma durable e idempotente (Tarea 30).

    Función PURA en el sentido requerido: determinista dado `(conn, now)`, sin lecturas de reloj
    de pared, sin scheduler ni asincronía. Selecciona los schedules `active` + `authorized=1`
    con `next_run_at <= now` y ejecuta cada ocurrencia vencida en SU PROPIA transacción
    financiera, de modo que el fallo/rollback de una no aborte las demás.

    Semántica de durabilidad/idempotencia (D07, DD-7, F10):
      - Crash ANTES del COMMIT ⇒ ROLLBACK total (sin fila de ejecución, sin débito, `next_run_at`
        intacto); el siguiente tick reintenta la ocurrencia limpiamente, exactamente una vez.
      - Tras el COMMIT ⇒ existe la fila `schedule_execution`; el reintento falla el `INSERT`
        sobre `UNIQUE(schedule_id, due_at)` y la ocurrencia se omite (sin doble efecto).

    Nota (alcance Tarea 30 + mínimo de Tarea 31): el camino de éxito es el foco. El fallo de
    negocio (fondos/límite) se registra con `outcome='failed'` SIN débito y avanza `next_run_at`
    (REC-10, Req. 11.2), el mínimo necesario para no dejar efectos financieros parciales ni el
    schedule atascado; se alinea con el contrato de la Tarea 31.

    Devuelve un `ProcessDueSummary` con contadores y el detalle por ocurrencia.
    """
    now_iso = clock.iso(now)
    summary = ProcessDueSummary()
    for schedule in repository.list_due_schedules(conn, now_iso):
        outcome = _process_one(conn, schedule, now)
        summary.outcomes.append(outcome)
        if outcome.status == "executed":
            summary.executed += 1
        elif outcome.status == "failed":
            summary.failed += 1
        else:
            summary.skipped += 1
    return summary
