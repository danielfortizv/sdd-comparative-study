"""Patrón de comando atómico de la Etapa 4 (Tarea 10; D-06, D-09, D-11, DK-03).

Compone, dentro de UNA sola `txn.financial_transaction` (`BEGIN IMMEDIATE`), los efectos de un
comando financiero: evento(s) de dominio, actualización de proyección(es), entrada de auditoría y
bump de versión de cuenta — de forma **atómica** (todo se confirma o todo se revierte,
fail-closed). La idempotencia (`Idempotency-Key`) y la validación de versión optimista esperada se
integran en la Tarea 11 sobre esta misma envoltura (DK-04: replay ANTES que versión).

Alcance de la Tarea 10: la infraestructura atómica evento+proyección+auditoría+versión. Un
"efecto por cuenta" (`AccountEffect`) describe el delta y el tipo de evento para un agregado; una
operación compuesta (p. ej. conversión) pasa varios efectos con el MISMO `operation_id`, cada uno
incrementando la versión de SU cuenta en +1 (D-09).
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass, field
from typing import Any

from . import audit, events, projections
from .txn import financial_transaction


class CommandError(RuntimeError):
    """Error de ejecución de un comando atómico (p. ej. cuenta inexistente)."""


@dataclass
class AccountEffect:
    """Efecto de un comando sobre UNA cuenta (un agregado)."""

    account_id: str
    event_type: str
    delta_minor: int           # con signo: débito negativo, crédito positivo
    event_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditSpec:
    """Entrada de auditoría a escribir atómicamente con los efectos del comando."""

    event_type: str
    outcome: str
    entity_ref: str | None
    payload: dict[str, Any]


def _account_meta(conn: sqlite3.Connection, account_id: str) -> tuple[str, str, str, int]:
    """Devuelve (public_id, kind, currency, version) de una cuenta o lanza CommandError."""
    row = conn.execute(
        "SELECT public_id, kind, currency, version FROM account WHERE id = ?",
        (account_id,),
    ).fetchone()
    if row is None:
        raise CommandError(f"Cuenta desconocida: {account_id}")
    return row["public_id"], row["kind"], row["currency"], int(row["version"])


def apply_effects_in_tx(
    conn: sqlite3.Connection,
    *,
    operation_id: str,
    effects: list[AccountEffect],
    occurred_at: str,
    audit_spec: AuditSpec | None = None,
) -> list[str]:
    """Aplica los efectos del comando DENTRO de una transacción YA abierta (sin commit).

    Por cada efecto: lee la versión actual, calcula la nueva (+1), persiste el evento de dominio
    (`aggregate_ver = new_version`), aplica el delta a la proyección, actualiza
    `account.balance_cents` y `account.version`. Si hay `audit_spec`, escribe la auditoría en la
    misma transacción. No hace commit (lo hace el context manager del llamador). Devuelve los
    `event_id` creados.

    Garantías: la `UNIQUE(aggregate_id, aggregate_ver)` del almacén de eventos impide aplicar dos
    veces la misma versión; cualquier fallo propaga para que el llamador revierta (fail-closed).
    """
    event_ids: list[str] = []
    for eff in effects:
        public_id, kind, currency, version = _account_meta(conn, eff.account_id)
        new_version = version + 1
        event_ids.append(
            events.append_event_no_commit(
                conn,
                event_type=eff.event_type,
                aggregate_id=eff.account_id,
                aggregate_ver=new_version,
                operation_id=operation_id,
                currency=currency,
                amount_minor=eff.delta_minor,
                payload=eff.event_payload,
                occurred_at=occurred_at,
            )
        )
        projections.apply_event_to_projection_no_commit(
            conn,
            account_id=eff.account_id,
            public_id=public_id,
            kind=kind,
            currency=currency,
            delta_minor=eff.delta_minor,
            new_version=new_version,
            updated_at=occurred_at,
        )
        conn.execute(
            "UPDATE account SET balance_cents = balance_cents + ?, version = ? WHERE id = ?",
            (eff.delta_minor, new_version, eff.account_id),
        )
    if audit_spec is not None:
        audit.append_in_tx(
            conn,
            event_type=audit_spec.event_type,
            outcome=audit_spec.outcome,
            entity_ref=audit_spec.entity_ref,
            occurred_at=occurred_at,
            payload=audit_spec.payload,
        )
    return event_ids


def run_command(
    conn: sqlite3.Connection,
    *,
    effects: list[AccountEffect],
    occurred_at: str,
    audit_spec: AuditSpec | None = None,
    operation_id: str | None = None,
) -> tuple[str, list[str]]:
    """Ejecuta un comando atómico: abre `financial_transaction` y aplica los efectos (D-11).

    Devuelve `(operation_id, event_ids)`. Un fallo en cualquier efecto revierte TODO (fail-closed).
    La idempotencia/versión esperada se añaden en la Tarea 11 envolviendo esta función.
    """
    op_id = operation_id or str(uuid.uuid4())
    with financial_transaction(conn):
        event_ids = apply_effects_in_tx(
            conn,
            operation_id=op_id,
            effects=effects,
            occurred_at=occurred_at,
            audit_spec=audit_spec,
        )
    return op_id, event_ids
