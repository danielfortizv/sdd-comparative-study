"""Verificación de invariantes post-carga de Shift Bank (Etapa 3, Tarea 22).

design.md §3.4 · requirements R10.4, R10.5 · AC-09.

Propósito
---------
Tras una corrida de carga contra la DB SQLite **sintética aislada** (Tareas 18–20), comprobar
que el sistema quedó en un estado financieramente correcto. Cualquier violación marca la corrida
como **FALLIDA** con independencia de los números de rendimiento (R10.5): el rendimiento jamás
rescata una corrida que rompió un invariante.

Tres invariantes (design.md §3.4):

1. **Conservación del dinero (R10.4).** El dinero no se crea ni se destruye. La fórmula NO se
   inventa: se DERIVA del modelo de datos real (`db.py`, `repository.py`, `ach_repository.py`,
   `service.py`, `ach_service.py`):

     - `account.balance_cents` guarda los saldos de las dos cuentas internas (checking/savings).
     - Una transferencia **interna** (`type='internal'`) debita el origen y abona el destino en
       la MISMA transacción (`repository.apply_transfer_in_tx`), de modo que la **suma de saldos
       se conserva**: el dinero permanece dentro del sistema.
     - Una transferencia **ACH** (`type='ach'`) debita el origen hacia un beneficiario EXTERNO
       (`ach_repository.debit_source_no_commit`): ese dinero **sale del sistema**. El débito
       ocurre al activarse la ACH (`pending`) y se mantiene en `settled`. Si la ACH falla, se
       reembolsa EXACTAMENTE UNA VEZ (`fail_and_refund_no_commit`, guarda `refunded=0→1`), con lo
       que el dinero **vuelve** a los saldos. Las ACH `pending_auth`/`expired` nunca debitaron.

     Por tanto el invariante de conservación es:

         total_inicial_sembrado
             == sum(account.balance_cents)
                + sum(transfer.amount_cents WHERE type='ach' AND status IN ('pending','settled'))

     El segundo sumando es el dinero "en vuelo o liquidado" que salió del sistema vía ACH y aún
     no fue reembolsado. El total inicial sembrado lo provee el llamador (el runner lo conoce de
     `isolation.py`); si no se provee, se calcula a partir del estado actual de forma
     conservadora (ver `compute_expected_total`), de modo que la verificación siga siendo útil.

2. **Ausencia de estados parciales (R10.4).** Ninguna transferencia/… queda en un estado
   intermedio inconsistente o en un `status` que la máquina de estados heredada prohíbe como
   estado de reposo. Se comprueban las columnas de estado REALES:

     - `transfer.status` debe pertenecer al catálogo de estados de reposo conocidos (internos en
       MAYÚSCULAS, ACH en minúsculas; ver `_INTERNAL_RESTING_STATES` / `_ACH_RESTING_STATES`).
     - Coherencia estado↔columnas: una interna `COMPLETED` debe tener `completed_at`; una ACH
       `settled` debe tener `settled_at`; una ACH `failed` debe tener `refunded=1` (el reembolso
       exactamente-una-vez ya se aplicó). Un débito-sin-crédito es imposible dentro de una sola
       transacción financiera, por lo que su manifestación observable es justamente esta
       incoherencia estado↔columna, que aquí se detecta.

3. **Integridad de la cadena de auditoría (R10.4), incluida el ancla de cola (§2.9).** Se invoca
   `audit.verify_chain(conn)` sobre la conexión de la DB de carga y se exige `ok is True`. Si
   devuelve `ok=False` (contenido manipulado, reordenamiento, eliminación intermedia o
   truncación del final detectada por el ancla), es un **FALLO**.

Semántica fail-loud (R10.5)
---------------------------
- API clara: `verify_invariants(db_path, expected_total_cents=None) -> InvariantReport` con
  `ok: bool` y `violations: list[InvariantViolation]`. Cualquier violación ⇒ `ok=False`.
- NO se tragan excepciones: una DB ausente, ilegible, sin el esquema esperado, o una cadena no
  verificable es un **FALLO** explícito (nunca un PASS). El runner debe tratar `ok=False` como
  corrida fallida INDEPENDIENTEMENTE del rendimiento.
- `assert_ok()` lanza `InvariantError` para los llamadores que prefieran excepción a inspección.

Este módulo usa SOLO la biblioteca estándar más el paquete `app` del backend (ya importable vía
`isolation.py`, que añade `backend/` a `sys.path`). NO importa `locust`/gevent (evita el
`monkey.patch_all`), coherente con `report.py`.
"""

from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

# `isolation` añade `backend/` a `sys.path` al importarse, de modo que `app.*` sea importable al
# ejecutar la verificación tanto desde el runner como de forma independiente. Importarlo aquí
# replica esa garantía sin arrastrar `locust`/gevent.
from . import isolation  # noqa: F401  (efecto colateral: backend en sys.path)


# --- Catálogo de estados de reposo REALES (derivado del código de servicio) ---
#
# Internos (service.py / repository.py): PENDING_MFA (esperando MFA, sin dinero movido),
# COMPLETED (dinero movido), EXPIRED (ventana MFA vencida), FAILED (rechazo sin débito).
_INTERNAL_RESTING_STATES = frozenset({"PENDING_MFA", "COMPLETED", "EXPIRED", "FAILED"})

# ACH (ach_service.py): pending_auth (sin débito), pending (debitado, en vuelo),
# settled (debitado, liquidado), failed (reembolsado una vez), expired (sin débito).
_ACH_RESTING_STATES = frozenset({"pending_auth", "pending", "settled", "failed", "expired"})

# Estados ACH que representan dinero DEBITADO que salió del sistema y NO fue reembolsado.
# (`failed` ya reembolsó; `pending_auth`/`expired` nunca debitaron.)
_ACH_OUTFLOW_STATES = frozenset({"pending", "settled"})


class InvariantError(RuntimeError):
    """La verificación de invariantes falló (fail-loud). La lanza `assert_ok()`.

    El mensaje enumera las violaciones detectadas; no incluye material sensible (saldos y montos
    son metadatos operativos de la DB sintética de carga, no PII/secretos).
    """


@dataclass(frozen=True)
class InvariantViolation:
    """Una violación concreta de invariante.

    Attributes:
        kind: categoría estable ('money_conservation' | 'partial_state' | 'audit_chain' |
            'precondition'). Permite al runner clasificar el fallo.
        detail: descripción legible de la violación (sin secretos).
    """

    kind: str
    detail: str


@dataclass
class InvariantReport:
    """Resultado de la verificación de invariantes post-carga.

    Attributes:
        ok: True SOLO si no hubo ninguna violación. Cualquier violación ⇒ False (R10.5).
        violations: lista de violaciones detectadas (vacía si `ok`).
        expected_total_cents: total de dinero esperado (invariante de conservación) usado en la
            comprobación, en centavos.
        observed_total_cents: total de dinero observado = suma de saldos + salida ACH no
            reembolsada, en centavos.
        balances_cents: saldos por tipo de cuenta observados (para diagnóstico).
        ach_outflow_cents: dinero debitado que salió por ACH (pending/settled), en centavos.
        audit_failed_seq / audit_reason: detalle del fallo de cadena si lo hubo (o None).
    """

    ok: bool
    violations: list[InvariantViolation] = field(default_factory=list)
    expected_total_cents: int | None = None
    observed_total_cents: int | None = None
    balances_cents: dict[str, int] = field(default_factory=dict)
    ach_outflow_cents: int = 0
    audit_failed_seq: int | None = None
    audit_reason: str | None = None

    def assert_ok(self) -> None:
        """Lanza `InvariantError` si la verificación no pasó (para llamadores fail-loud)."""
        if not self.ok:
            lines = "; ".join(f"[{v.kind}] {v.detail}" for v in self.violations)
            raise InvariantError(
                f"verificación de invariantes FALLIDA ({len(self.violations)} violación/es): "
                f"{lines}"
            )


# ---------------------------------------------------------------------------
# Lecturas derivadas del esquema real (nunca fabrican; leen las tablas reales)
# ---------------------------------------------------------------------------
def read_balances(conn: sqlite3.Connection) -> dict[str, int]:
    """Lee los saldos por tipo de cuenta (centavos) desde la tabla real `account`."""
    rows = conn.execute("SELECT kind, balance_cents FROM account").fetchall()
    return {r["kind"]: int(r["balance_cents"]) for r in rows}


def read_ach_outflow_cents(conn: sqlite3.Connection) -> int:
    """Suma el dinero ACH debitado que salió del sistema y NO fue reembolsado.

    Deriva de `ach_service`/`ach_repository`: una ACH `pending`/`settled` debitó el origen hacia
    un beneficiario externo (dinero fuera del sistema); una `failed` ya reembolsó y una
    `pending_auth`/`expired` nunca debitó. Por eso solo se suman `pending` y `settled`.
    """
    placeholders = ",".join("?" for _ in _ACH_OUTFLOW_STATES)
    row = conn.execute(
        f"""SELECT COALESCE(SUM(amount_cents), 0) AS total
            FROM transfer
            WHERE type = 'ach' AND status IN ({placeholders})""",
        tuple(sorted(_ACH_OUTFLOW_STATES)),
    ).fetchone()
    return int(row["total"])


def compute_observed_total(conn: sqlite3.Connection) -> tuple[int, dict[str, int], int]:
    """Calcula el total observado = suma de saldos + salida ACH no reembolsada.

    Devuelve `(observed_total_cents, balances_cents, ach_outflow_cents)`.
    """
    balances = read_balances(conn)
    ach_outflow = read_ach_outflow_cents(conn)
    observed = sum(balances.values()) + ach_outflow
    return observed, balances, ach_outflow


def compute_expected_total(conn: sqlite3.Connection) -> int:
    """Total de conservación ESPERADO cuando el llamador no lo provee (fallback conservador).

    El invariante de conservación es `inicial == saldos + salida_ACH_no_reembolsada`. Como el
    total inicial sembrado no está en una tabla (los saldos cambian durante la corrida), cuando
    el llamador no lo pasa se reconstruye el total ACTUAL (`compute_observed_total`): esto NO
    detecta pérdida/creación de dinero por sí solo (para eso el runner DEBE pasar el total inicial
    conocido de `isolation.py`), pero mantiene la verificación consistente y nunca fabrica un
    número arbitrario. El runner de carga (Tarea 20) pasa el inicial real; esta ruta es un apoyo
    para invocaciones manuales/diagnósticas.
    """
    observed, _balances, _ach = compute_observed_total(conn)
    return observed


# ---------------------------------------------------------------------------
# Comprobaciones individuales (cada una devuelve una lista de violaciones)
# ---------------------------------------------------------------------------
def check_money_conservation(
    conn: sqlite3.Connection, expected_total_cents: int, observed_total_cents: int
) -> list[InvariantViolation]:
    """Compara el total esperado con el observado (conservación del dinero, R10.4)."""
    if observed_total_cents != expected_total_cents:
        delta = observed_total_cents - expected_total_cents
        sign = "creado" if delta > 0 else "destruido"
        return [
            InvariantViolation(
                kind="money_conservation",
                detail=(
                    f"conservación rota: esperado {expected_total_cents} centavos, observado "
                    f"{observed_total_cents} centavos (dinero {sign}: {abs(delta)} centavos). "
                    "observado = suma de saldos + salida ACH (pending/settled) no reembolsada."
                ),
            )
        ]
    return []


def check_no_partial_states(conn: sqlite3.Connection) -> list[InvariantViolation]:
    """Detecta estados de reposo prohibidos e incoherencias estado↔columnas (R10.4).

    Revisa la tabla REAL `transfer`:
      - `status` debe estar en el catálogo de reposo (interno en MAYÚSCULAS / ACH en minúsculas).
      - interna `COMPLETED` ⇒ `completed_at` no nulo (movimiento consolidado).
      - ACH `settled`       ⇒ `settled_at` no nulo (liquidación consolidada).
      - ACH `failed`        ⇒ `refunded = 1` (reembolso exactamente-una-vez ya aplicado).
    """
    violations: list[InvariantViolation] = []
    rows = conn.execute(
        """SELECT id, type, status, completed_at, settled_at, refunded
           FROM transfer"""
    ).fetchall()

    for row in rows:
        tid = row["id"]
        ttype = row["type"]
        status = row["status"]

        if ttype == "ach":
            if status not in _ACH_RESTING_STATES:
                violations.append(
                    InvariantViolation(
                        kind="partial_state",
                        detail=(
                            f"ACH {tid} en estado no-reposo '{status}' "
                            f"(permitidos: {sorted(_ACH_RESTING_STATES)})"
                        ),
                    )
                )
                continue
            if status == "settled" and row["settled_at"] is None:
                violations.append(
                    InvariantViolation(
                        kind="partial_state",
                        detail=f"ACH {tid} 'settled' sin settled_at (liquidación parcial)",
                    )
                )
            if status == "failed" and int(row["refunded"] or 0) != 1:
                violations.append(
                    InvariantViolation(
                        kind="partial_state",
                        detail=(
                            f"ACH {tid} 'failed' con refunded={row['refunded']} "
                            "(reembolso no aplicado: estado parcial)"
                        ),
                    )
                )
        else:
            # Transferencia interna (type='internal' o filas heredadas sin ACH).
            if status not in _INTERNAL_RESTING_STATES:
                violations.append(
                    InvariantViolation(
                        kind="partial_state",
                        detail=(
                            f"transferencia interna {tid} en estado no-reposo '{status}' "
                            f"(permitidos: {sorted(_INTERNAL_RESTING_STATES)})"
                        ),
                    )
                )
                continue
            if status == "COMPLETED" and row["completed_at"] is None:
                violations.append(
                    InvariantViolation(
                        kind="partial_state",
                        detail=(
                            f"transferencia interna {tid} 'COMPLETED' sin completed_at "
                            "(movimiento parcial)"
                        ),
                    )
                )

    return violations


def check_audit_chain(conn: sqlite3.Connection) -> tuple[list[InvariantViolation], int | None, str | None]:
    """Verifica la cadena de auditoría íntegra, incluida el ancla (R10.4, §2.9).

    Invoca `audit.verify_chain`; si `ok` es False lo convierte en una violación. Devuelve
    `(violations, failed_seq, reason)`.
    """
    import app.audit as audit

    result = audit.verify_chain(conn)
    if result.ok:
        return [], None, None
    return (
        [
            InvariantViolation(
                kind="audit_chain",
                detail=(
                    f"cadena de auditoría NO íntegra (seq={result.failed_seq}): {result.reason}"
                ),
            )
        ],
        result.failed_seq,
        result.reason,
    )


# ---------------------------------------------------------------------------
# API principal (fail-loud)
# ---------------------------------------------------------------------------
def verify_invariants(
    db_path: str | Path,
    *,
    expected_total_cents: int | None = None,
) -> InvariantReport:
    """Verifica los invariantes financieros post-carga sobre la DB de carga (R10.4/R10.5).

    Args:
        db_path: ruta a la DB SQLite de carga (sintética aislada). Debe existir y ser legible.
        expected_total_cents: total de dinero esperado (invariante de conservación), en centavos.
            El runner lo provee desde `isolation.py` (saldos sembrados iniciales). Si es None, se
            usa el total ACTUAL reconstruido (`compute_expected_total`) como apoyo diagnóstico
            (esa ruta no detecta pérdida/creación por sí sola; para la verificación fuerte el
            runner DEBE pasar el inicial conocido).

    Returns:
        `InvariantReport` con `ok` y la lista de violaciones. Cualquier violación ⇒ `ok=False`.

    Semántica fail-loud (R10.5): una DB ausente/ilegible/sin esquema o una cadena no verificable
    NO se trata como PASS; se reporta como violación (`ok=False`). No se tragan excepciones de
    forma que oculten un fallo: los errores de acceso/consulta se convierten en violaciones
    explícitas y el reporte resultante es no-ok.
    """
    path = Path(db_path)

    # Precondición fail-loud: la DB debe existir. Una DB ausente NUNCA es un PASS.
    if not path.is_file():
        return InvariantReport(
            ok=False,
            violations=[
                InvariantViolation(
                    kind="precondition",
                    detail=(
                        f"la DB de carga no existe o no es un archivo: {path}. Un estado "
                        "no verificable es un FALLO, no un PASS."
                    ),
                )
            ],
        )

    conn: sqlite3.Connection | None = None
    try:
        import app.db as db

        conn = db.get_connection(path)

        # Reconstrucción del total observado desde las tablas reales.
        observed_total, balances, ach_outflow = compute_observed_total(conn)

        expected = (
            expected_total_cents
            if expected_total_cents is not None
            else compute_expected_total(conn)
        )

        violations: list[InvariantViolation] = []
        violations += check_money_conservation(conn, expected, observed_total)
        violations += check_no_partial_states(conn)
        audit_violations, failed_seq, reason = check_audit_chain(conn)
        violations += audit_violations

        return InvariantReport(
            ok=len(violations) == 0,
            violations=violations,
            expected_total_cents=expected,
            observed_total_cents=observed_total,
            balances_cents=balances,
            ach_outflow_cents=ach_outflow,
            audit_failed_seq=failed_seq,
            audit_reason=reason,
        )
    except sqlite3.Error as exc:
        # Un error de acceso/consulta (p. ej. esquema ausente) es un FALLO explícito, no un PASS.
        return InvariantReport(
            ok=False,
            violations=[
                InvariantViolation(
                    kind="precondition",
                    detail=(
                        f"no se pudo verificar la DB de carga ({type(exc).__name__}): {exc}. "
                        "Un estado no verificable es un FALLO."
                    ),
                )
            ],
        )
    finally:
        if conn is not None:
            conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="verify_invariants",
        description=(
            "Verificación de invariantes post-carga de Shift Bank (Etapa 3, Tarea 22): "
            "conservación del dinero, ausencia de estados parciales y cadena de auditoría íntegra "
            "(incluida el ancla). Cualquier violación ⇒ salida != 0, independientemente del "
            "rendimiento (R10.5)."
        ),
    )
    parser.add_argument("db_path", help="Ruta a la DB SQLite de carga (sintética aislada).")
    parser.add_argument(
        "--expected-total-cents",
        type=int,
        default=None,
        help=(
            "Total de dinero inicial sembrado (centavos) para la conservación. El runner lo "
            "pasa desde isolation.py. Si se omite, se usa el total actual (apoyo diagnóstico)."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI: verifica la DB y devuelve 0 solo si TODOS los invariantes se cumplen (fail-loud)."""
    args = _build_parser().parse_args(argv)
    report = verify_invariants(
        args.db_path, expected_total_cents=args.expected_total_cents
    )

    print("=== verify_invariants: RESULT ===")
    print(f"  db_path:              {args.db_path}")
    print(f"  ok:                   {report.ok}")
    print(f"  expected_total_cents: {report.expected_total_cents}")
    print(f"  observed_total_cents: {report.observed_total_cents}")
    print(f"  balances_cents:       {report.balances_cents}")
    print(f"  ach_outflow_cents:    {report.ach_outflow_cents}")
    if report.audit_reason is not None:
        print(f"  audit_failed_seq:     {report.audit_failed_seq}")
        print(f"  audit_reason:         {report.audit_reason}")
    if report.violations:
        print("  violaciones:")
        for v in report.violations:
            print(f"    - [{v.kind}] {v.detail}")
    else:
        print("  violaciones:          (ninguna)")

    if not report.ok:
        print(
            "[verify_invariants] FALLO: invariantes violados → corrida FALLIDA "
            "independientemente del rendimiento (R10.5).",
            file=sys.stderr,
        )
        return 1
    print("[verify_invariants] OK: invariantes preservados y cadena íntegra.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
