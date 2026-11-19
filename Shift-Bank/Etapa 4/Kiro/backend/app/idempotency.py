"""Idempotencia y concurrencia optimista de la Etapa 4 (Tarea 11; D-13, D-14, DK-04).

Integra sobre el patrón de comando (`command.py`) dos controles exigidos por las decisiones
comunes, en el ORDEN correcto (DK-04): el replay idempotente se evalúa **ANTES** que la validación
de versión de cuenta.

- `Idempotency-Key` UUID obligatorio (D-13): replay exacto (misma clave + mismo payload) devuelve
  el resultado original SIN nuevos efectos; reuse con payload distinto -> 409 (IDEMPOTENCY_CONFLICT).
- Versión de cuenta esperada (D-14): si no coincide con la actual -> 409 (ACCOUNT_VERSION_CONFLICT).

Todo el efecto (eventos + proyección + versión + auditoría + registro de idempotencia) se confirma
atómicamente dentro de UNA `financial_transaction` (D-11): el registro de idempotencia se inserta
en la misma transacción que aplica los efectos, de modo que no exista efecto sin registro ni
registro sin efecto.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Any

from . import command
from .txn import financial_transaction


class IdempotencyError(Exception):
    """Error de idempotencia/versión con `code` estable y `status` HTTP para el borde."""

    def __init__(self, code: str, message: str, status: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


@dataclass
class CommandResult:
    status_code: int
    response: dict[str, Any]
    replayed: bool = False


def require_uuid_key(raw: str | None) -> str:
    """Valida que el header `Idempotency-Key` sea un UUID; lanza IdempotencyError si no (D-13)."""
    if raw is None or str(raw).strip() == "":
        raise IdempotencyError("IDEMPOTENCY_KEY_REQUIRED",
                               "Falta el header Idempotency-Key", 400)
    try:
        uuid.UUID(str(raw))
    except (ValueError, AttributeError, TypeError) as exc:
        raise IdempotencyError("IDEMPOTENCY_KEY_INVALID",
                               "Idempotency-Key debe ser un UUID válido", 400) from exc
    return str(raw)


def request_hash(operation: str, payload: dict[str, Any]) -> str:
    """Hash canónico determinista del payload normalizado (para distinguir replay vs reuse)."""
    canonical = json.dumps(
        {"op": operation, "payload": payload},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _lookup(conn: sqlite3.Connection, key: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM idempotency_key WHERE id = ?", (key,)).fetchone()


def execute_idempotent_command(
    conn: sqlite3.Connection,
    *,
    idempotency_key: str,
    operation: str,
    request_payload: dict[str, Any],
    expected_versions: dict[str, int],
    effects: list[command.AccountEffect],
    occurred_at: str,
    build_response,
    audit_spec: command.AuditSpec | None = None,
) -> CommandResult:
    """Ejecuta un comando con idempotencia + versión optimista, atómico (D-11, D-13, D-14, DK-04).

    Orden (DK-04):
    1. Validar que la clave es UUID (lo hace el borde con `require_uuid_key`, aquí se asume ya).
    2. **Replay idempotente ANTES que versión:** si la clave existe y el `request_hash` coincide,
       devolver la respuesta original (replay, sin efectos). Si existe con hash distinto -> 409
       IDEMPOTENCY_CONFLICT.
    3. **Versión optimista:** por cada cuenta en `expected_versions`, comparar con
       `account.version`; mismatch -> 409 ACCOUNT_VERSION_CONFLICT.
    4. Aplicar efectos + auditoría + registro de idempotencia en UNA transacción.

    `build_response(event_ids) -> dict` construye la respuesta a persistir/replayar.
    """
    rhash = request_hash(operation, request_payload)

    # (2) Replay idempotente ANTES que versión (DK-04). Lectura fuera de transacción de escritura.
    existing = _lookup(conn, idempotency_key)
    if existing is not None:
        if existing["request_hash"] == rhash:
            return CommandResult(
                status_code=existing["status_code"],
                response=json.loads(existing["response_json"]),
                replayed=True,
            )
        raise IdempotencyError(
            "IDEMPOTENCY_CONFLICT",
            "Idempotency-Key reutilizada con un payload distinto", 409)

    with financial_transaction(conn):
        # Re-chequear idempotencia dentro de la transacción (carrera entre dos requests con la
        # misma clave): si otro la insertó, tratar como replay/conflict de forma consistente.
        inside = _lookup(conn, idempotency_key)
        if inside is not None:
            if inside["request_hash"] == rhash:
                return CommandResult(
                    status_code=inside["status_code"],
                    response=json.loads(inside["response_json"]),
                    replayed=True,
                )
            raise IdempotencyError(
                "IDEMPOTENCY_CONFLICT",
                "Idempotency-Key reutilizada con un payload distinto", 409)

        # (3) Versión optimista por cuenta (tras el replay, DK-04).
        for account_id, expected in expected_versions.items():
            row = conn.execute(
                "SELECT version FROM account WHERE id = ?", (account_id,)).fetchone()
            if row is None:
                raise IdempotencyError("NOT_FOUND", f"Cuenta desconocida: {account_id}", 404)
            if int(row["version"]) != int(expected):
                raise IdempotencyError(
                    "ACCOUNT_VERSION_CONFLICT",
                    "La versión esperada de la cuenta no coincide (solicitud obsoleta)", 409)

        # (4) Aplicar efectos + auditoría en la MISMA transacción.
        op_id = str(uuid.uuid4())
        event_ids = command.apply_effects_in_tx(
            conn,
            operation_id=op_id,
            effects=effects,
            occurred_at=occurred_at,
            audit_spec=audit_spec,
        )
        response = build_response(event_ids)
        # Registro de idempotencia atómico con el efecto (D-13-4).
        conn.execute(
            """INSERT INTO idempotency_key
               (id, operation, request_hash, response_json, status_code, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (idempotency_key, operation, rhash,
             json.dumps(response, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
             200, occurred_at),
        )
    return CommandResult(status_code=200, response=response, replayed=False)
