"""Auditoría inmutable verificable: serialización canónica, cadena HMAC y ancla (Etapa 3, Tarea 10).

Implementa el núcleo de la bitácora append-only encadenada con HMAC del diseño §2.2, §2.3 y §2.9,
sobre el esquema `audit_log`/`audit_anchor` creado en `db.migrate` (Tarea 9). Usa exclusivamente
la biblioteca estándar (`hmac`, `hashlib`, `json`) y la clave HMAC externa `SHIFT_AUDIT_HMAC_KEY`
provista por entorno (fail-closed, R2.1/R6.3). No implementa criptografía propia (R18.2).

Decisiones honradas (design.md §2.2–§2.3, §2.9; requirements R5.4, R6.3, R6.4, R6.6):

- **Fail-closed de clave (R6.3):** `load_key()` lee `SHIFT_AUDIT_HMAC_KEY` vía
  `config.get_audit_hmac_key_raw()`; si falta o está vacía lanza `AuditConfigError`. El material
  de clave NUNCA se registra ni aparece en mensajes de error (R2.6/R15.2).

- **Serialización canónica determinista (R6.3, §2.2):** `_canonical(entry)` produce bytes UTF-8
  de un JSON con `sort_keys=True` y `separators=(",", ":")` (sin espacios), de modo que el mismo
  evento lógico produzca SIEMPRE los mismos bytes con independencia del orden de las claves de
  entrada. El `payload` se re-canonicaliza igual (claves ordenadas, sin espacios) antes de
  incluirse, para que un payload con las mismas claves/valores en distinto orden encadene igual.

- **Material cubierto por el HMAC — EXCLUYE `seq` (esquema de encadenado, §2.3):** el `seq` lo
  asigna SQLite por AUTOINCREMENT en el INSERT, por lo que no se conoce antes de insertar. Para
  que `verify_chain` recompute EXACTAMENTE el mismo material que `append_in_tx`, el HMAC se
  calcula sobre los campos conocidos de forma determinista —`event_type`, `outcome`,
  `entity_ref`, `occurred_at`, `payload_canónico`— y se **encadena** con el `prev_hmac`. El
  orden total y la posición quedan ligados por el propio encadenado (`prev_hmac`), y la
  contigüidad de `seq` se comprueba aparte en `verify_chain`. Este es el esquema CANÓNICO del que
  dependen las tareas 11 y 12: NO incluir `seq` dentro del material del HMAC.

    entry_hmac = HMAC_SHA256(key, prev_hmac.encode("utf-8") + _canonical(entry)).hexdigest()

  donde `_canonical(entry)` serializa el objeto:

    {"entity_ref":<str|null>,"event_type":<str>,"occurred_at":<str>,
     "outcome":<str>,"payload":<objeto JSON canónico>}

  (las claves salen ordenadas alfabéticamente por `sort_keys=True`; el ejemplo muestra el orden
  resultante). La génesis usa `prev_hmac = ""`.

- **Ancla de cola (R6.6, §2.9):** cada `append_in_tx` actualiza (UPSERT) la fila única
  `audit_anchor(id=1)` con el `last_seq`/`last_hmac` de la nueva entrada, DENTRO de la misma
  transacción del llamador. `verify_chain` compara la cola real con el ancla y detecta la
  truncación del final (eliminar las últimas entradas conservando un estado consistente), dentro
  de los límites del modelo de amenazas (si el atacante controla también el ancla y la clave, la
  truncación vuelve a ser indetectable; no se reclama inmutabilidad absoluta).

- **Verificación en tiempo constante (§2.3):** la comparación de HMAC usa `hmac.compare_digest`.

Límite transaccional (§2.3): `append_in_tx` NO hace commit; se ejecuta DENTRO de la transacción
abierta por el llamador (`txn.financial_transaction`), logrando atomicidad dinero+auditoría.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
from dataclasses import dataclass
from typing import Any

from . import config

# --- Catálogo de tipos de evento y resultados (design.md §5.2, Tarea 12) ------
#
# Constantes canónicas de `event_type` y `outcome` para que los servicios emisores
# (service, ach_service, recurring_service) compartan UN solo catálogo y no haya
# divergencia de literales. Son metadatos NO sensibles; el `payload` que acompaña a
# cada evento NUNCA incluye cuenta/routing/snapshot en claro ni cifrado (R5.6, §2.1).

# Resultados (columna `outcome`).
OUTCOME_SUCCESS = "success"
OUTCOME_REJECTED = "rejected"

# Transferencias internas (origen: `service`).
EVENT_INTERNAL_TRANSFER_COMPLETED = "INTERNAL_TRANSFER_COMPLETED"
EVENT_MFA_CONFIRMED = "MFA_CONFIRMED"

# Rechazos de transferencias internas / MFA (Tarea 14, design.md §2.7, §5.2; R5.3/R7.3/R7.4).
#
# Eventos `outcome='rejected'` que registran un INTENTO rechazado SIN mover saldos. Un rechazo
# NUNCA acompaña a una mutación bancaria confirmada: se audita en su propia transacción pequeña
# (solo inserta la fila de auditoría) o junto a un cambio de estado NO financiero (p. ej.
# marcar FAILED sin débito). Sus payloads son NO sensibles.
#
# - MFA_FAILED: PIN inválido en la confirmación (interna o ACH). El flujo heredado deja la
#   transferencia PENDING_MFA/pending_auth intacta (permite reintento); solo se añade el intento
#   auditado, sin débito ni cambio de estado.
# - INTERNAL_TRANSFER_REJECTED: una transferencia interna que se rechaza al confirmar/aplicar
#   (p. ej. límite superado o fondos insuficientes al confirmar), marcada FAILED SIN débito.
EVENT_MFA_FAILED = "MFA_FAILED"
EVENT_INTERNAL_TRANSFER_REJECTED = "INTERNAL_TRANSFER_REJECTED"

# Transferencias ACH (origen: `ach_service`).
EVENT_ACH_PENDING = "ACH_PENDING"
EVENT_ACH_PENDING_AUTH = "ACH_PENDING_AUTH"
EVENT_ACH_CONFIRMED = "ACH_CONFIRMED"
EVENT_ACH_SETTLED = "ACH_SETTLED"
EVENT_ACH_FAILED_REFUNDED = "ACH_FAILED_REFUNDED"

# Rechazo ACH (fondos/límite al confirmar) — marca `failed` SIN débito (Tarea 14; R5.3/R7.4).
EVENT_ACH_REJECTED = "ACH_REJECTED"

# Pagos recurrentes (origen: `recurring_service`).
EVENT_RECURRING_EXECUTED = "RECURRING_EXECUTED"
EVENT_RECURRING_FAILED = "RECURRING_FAILED"

# Configuración sensible (Tarea 13, design.md §2.7, §5.2; R5.2/R5.5).
#
# Acciones administrativas/de configuración que NO mueven saldos pero SÍ deben quedar auditadas,
# cada una atómica con su propio cambio (misma `financial_transaction`). Las consultas de solo
# lectura (listar beneficiarios/límites/recurrentes, historial) NO generan auditoría (R5.5).
# Orígenes: alta/baja de beneficiario (router `beneficiaries`), actualización de límites
# (`limit_service`), ciclo de vida de schedule (`recurring_service`). Los payloads que acompañan
# a estos eventos son NO sensibles (p. ej. `{bank}` + cuenta enmascarada, `{per_transfer_cents,
# daily_cents}`, `{status, frequency}`); nunca cuenta/routing en claro ni token `enc:` (R5.6).

# Beneficiarios (origen: router `beneficiaries` sobre `ach_repository`).
EVENT_BENEFICIARY_CREATED = "BENEFICIARY_CREATED"
EVENT_BENEFICIARY_DELETED = "BENEFICIARY_DELETED"

# Límites de transferencia (origen: `limit_service`).
EVENT_LIMIT_UPDATED = "LIMIT_UPDATED"

# Ciclo de vida de schedule recurrente (origen: `recurring_service`).
EVENT_SCHEDULE_PAUSED = "SCHEDULE_PAUSED"
EVENT_SCHEDULE_RESUMED = "SCHEDULE_RESUMED"
EVENT_SCHEDULE_CANCELLED = "SCHEDULE_CANCELLED"


class AuditConfigError(RuntimeError):
    """Clave HMAC de auditoría ausente o vacía (fail-closed en carga/arranque, R6.3).

    Se lanza por `load_key()` cuando `SHIFT_AUDIT_HMAC_KEY` falta o está vacía. El mensaje
    identifica QUÉ variable falla pero NUNCA incluye material de clave (R2.6/R15.2).
    """


@dataclass(frozen=True)
class VerifyResult:
    """Resultado de `verify_chain`.

    Attributes:
        ok: True si la cadena completa es íntegra (y coherente con el ancla).
        failed_seq: `seq` de la primera entrada que falla la verificación, o None si `ok`.
            Para fallos relativos al ancla sin una fila concreta (p. ej. ancla por delante de
            una cola vacía) se reporta el `seq` esperado por el ancla.
        reason: descripción legible del primer fallo, o None si `ok`.
    """

    ok: bool
    failed_seq: int | None = None
    reason: str | None = None


def load_key() -> bytes:
    """Carga la clave HMAC de auditoría desde el entorno (fail-closed, R6.3).

    Lee `SHIFT_AUDIT_HMAC_KEY` vía `config.get_audit_hmac_key_raw()` y la devuelve como bytes
    UTF-8. No cachea: cada llamada vuelve a leer el entorno (coherente con `crypto.load_keys`),
    de modo que las pruebas que cambian la variable con `monkeypatch` ven el estado actual.

    Returns:
        La clave HMAC como `bytes` (codificación UTF-8 del valor crudo del entorno).

    Raises:
        AuditConfigError: si la variable está ausente o vacía (fail-closed). El mensaje nunca
            incluye material de clave (R2.6).
    """
    raw = config.get_audit_hmac_key_raw()
    if not raw or not raw.strip():
        raise AuditConfigError(
            f"{config.ENV_AUDIT_HMAC_KEY} ausente o vacío: se requiere para la cadena de auditoría"
        )
    return raw.encode("utf-8")


def _canonical(entry: dict[str, Any]) -> bytes:
    """Serialización canónica determinista del material encadenado de una entrada (§2.2).

    Toma el dict de campos del evento y produce bytes UTF-8 de un JSON con claves ordenadas y
    separadores compactos. El material canónico EXCLUYE `seq` (asignado por AUTOINCREMENT en el
    INSERT; ver nota de módulo) e incluye exactamente estos campos del evento:

        event_type   (str)        — tipo del evento
        outcome      (str)        — "success" | "rejected"
        entity_ref   (str | None) — referencia pública (nunca id interno ni PII)
        occurred_at  (str)        — timestamp ISO-8601 UTC
        payload      (objeto)     — metadatos NO sensibles, re-canonicalizado (claves ordenadas)

    El `payload` se normaliza recursivamente vía el propio `json.dumps(sort_keys=True)`, por lo
    que dos payloads con las mismas claves/valores en distinto orden producen los MISMOS bytes
    (independencia del orden de claves, R6.3). Separadores `(",", ":")` eliminan todo espacio.

    Returns:
        Bytes UTF-8 de la serialización canónica (entrada del HMAC).
    """
    canonical_obj = {
        "event_type": entry["event_type"],
        "outcome": entry["outcome"],
        "entity_ref": entry["entity_ref"],
        "occurred_at": entry["occurred_at"],
        "payload": entry["payload"],
    }
    # sort_keys ordena TANTO las claves de primer nivel COMO las anidadas del payload;
    # ensure_ascii=False mantiene UTF-8 real (luego .encode); separadores sin espacios.
    text = json.dumps(
        canonical_obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return text.encode("utf-8")


def _compute_entry_hmac(key: bytes, prev_hmac: str, entry: dict[str, Any]) -> str:
    """Calcula `entry_hmac = HMAC-SHA256(key, prev_hmac_utf8 || canonical(entry))` en hex (§2.3).

    La génesis usa `prev_hmac = ""` (cadena vacía → 0 bytes de prefijo). El resultado es el
    digest hexadecimal en minúsculas de SHA-256.
    """
    msg = prev_hmac.encode("utf-8") + _canonical(entry)
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def _canonical_payload_text(payload: dict[str, Any] | None) -> str:
    """Serializa el `payload` a su JSON canónico (string) para persistir en la columna `payload`.

    Usa las MISMAS opciones de canonicalización que `_canonical` (`sort_keys`, separadores
    compactos, UTF-8) de modo que el texto almacenado reproduzca, al releerse y recanonicalizarse,
    el mismo material que entró al HMAC. `None` se persiste como objeto vacío `{}` para mantener
    la columna NOT NULL y un payload siempre-objeto.
    """
    obj: dict[str, Any] = {} if payload is None else payload
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def append_in_tx(
    conn: sqlite3.Connection,
    *,
    event_type: str,
    outcome: str,
    entity_ref: str | None,
    occurred_at: str,
    payload: dict[str, Any] | None,
) -> int:
    """Añade una entrada encadenada a `audit_log` DENTRO de la transacción del llamador (§2.3).

    Pasos (sin commit; la transacción la posee el llamador, p. ej. `financial_transaction`):

    1. Lee la cola: `(seq, entry_hmac)` de la última fila (`ORDER BY seq DESC LIMIT 1`). Si no
       hay ninguna, `prev_hmac = ""` (génesis).
    2. Calcula `entry_hmac = HMAC-SHA256(key, prev_hmac || canonical(entry))` (hex). El material
       canónico EXCLUYE `seq` (ver nota de módulo); el orden/posición quedan ligados por
       `prev_hmac` y la contigüidad de `seq` la comprueba `verify_chain`.
    3. INSERT de la fila (SQLite asigna `seq` por AUTOINCREMENT). El `payload` se persiste como
       su JSON canónico (string).
    4. UPSERT de `audit_anchor(id=1)` con `last_seq`/`last_hmac` de la nueva entrada, en la MISMA
       transacción (ancla de cola, §2.9).

    No captura excepciones: si algo falla, se propaga para que el context manager del llamador
    haga ROLLBACK (atomicidad dinero+auditoría, R7.1/R7.2).

    Args:
        conn: conexión SQLite con una transacción YA abierta por el llamador.
        event_type: tipo del evento (catálogo §5.2).
        outcome: "success" | "rejected".
        entity_ref: referencia pública de la entidad (nunca id interno ni PII); puede ser None.
        occurred_at: timestamp ISO-8601 UTC del evento.
        payload: metadatos NO sensibles (dict) o None.

    Returns:
        El `seq` asignado a la nueva entrada.
    """
    key = load_key()

    row = conn.execute(
        "SELECT seq, entry_hmac FROM audit_log ORDER BY seq DESC LIMIT 1"
    ).fetchone()
    prev_hmac = "" if row is None else row["entry_hmac"]

    # Canonicalizar el payload una sola vez: el texto persistido y el material del HMAC derivan
    # del MISMO objeto re-serializado, garantizando que verify_chain recompute lo mismo.
    payload_obj: dict[str, Any] = {} if payload is None else payload
    entry = {
        "event_type": event_type,
        "outcome": outcome,
        "entity_ref": entity_ref,
        "occurred_at": occurred_at,
        "payload": payload_obj,
    }
    entry_hmac = _compute_entry_hmac(key, prev_hmac, entry)
    payload_text = _canonical_payload_text(payload_obj)

    cur = conn.execute(
        """INSERT INTO audit_log
           (event_type, outcome, entity_ref, occurred_at, payload, prev_hmac, entry_hmac)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (event_type, outcome, entity_ref, occurred_at, payload_text, prev_hmac, entry_hmac),
    )
    new_seq = int(cur.lastrowid)

    # Ancla de cola (§2.9): UPSERT de la fila única id=1 con la nueva cola. En la misma
    # transacción, de modo que ancla y entrada se confirman/revierten juntas.
    conn.execute(
        """INSERT INTO audit_anchor (id, last_seq, last_hmac)
           VALUES (1, ?, ?)
           ON CONFLICT(id) DO UPDATE SET last_seq = excluded.last_seq,
                                         last_hmac = excluded.last_hmac""",
        (new_seq, entry_hmac),
    )

    return new_seq


def verify_chain(conn: sqlite3.Connection) -> VerifyResult:
    """Verifica la integridad de la cadena recomputando los HMAC (§2.5, §2.9; R6.4/R6.6).

    Recorre `audit_log` por `seq` ascendente y comprueba, en orden, para cada fila:

    (a) **Manipulación de contenido** — el `entry_hmac` almacenado coincide con el recomputado
        a partir de `prev_hmac` + `canonical(fila)` (comparación en tiempo constante).
    (b) **Reordenamiento / cadena rota** — el `prev_hmac` de la fila es igual al `entry_hmac` de
        la fila anterior (o "" para la génesis).
    (c) **Eliminación intermedia** — los `seq` son contiguos y crecientes (un hueco revela que se
        borró una entrada intermedia).
    (d) **Truncación del final (ancla, §2.9)** — tras validar la cola, el `audit_anchor(id=1)`
        debe referenciar el `seq`/`entry_hmac` de la ÚLTIMA fila presente. Si el ancla apunta a
        un `seq` mayor que el último presente, se detecta truncación.

    La columna `payload` se re-parsea con `json.loads` y se re-canonicaliza al recomputar, de
    modo que el material del HMAC coincide con el que calculó `append_in_tx`.

    Returns:
        `VerifyResult(ok=True)` si la cadena es íntegra y coherente con el ancla; en caso
        contrario `ok=False` con el `seq` del primer fallo y una razón legible.
    """
    try:
        key = load_key()
    except AuditConfigError as exc:
        return VerifyResult(ok=False, failed_seq=None, reason=str(exc))

    rows = conn.execute(
        """SELECT seq, event_type, outcome, entity_ref, occurred_at, payload, prev_hmac, entry_hmac
           FROM audit_log ORDER BY seq ASC"""
    ).fetchall()

    expected_prev = ""          # prev_hmac esperado para la génesis
    expected_seq = 1            # seq contiguo esperado (AUTOINCREMENT arranca en 1)
    last_seq = 0
    last_hmac = ""

    for row in rows:
        seq = int(row["seq"])

        row_failure = _verify_chain_row(key, row, seq, expected_seq, expected_prev)
        if row_failure is not None:
            return row_failure

        expected_prev = row["entry_hmac"]
        expected_seq = seq + 1
        last_seq = seq
        last_hmac = row["entry_hmac"]

    # (d) Ancla de cola (§2.9): detecta truncación del final conservando un estado consistente.
    return _verify_tail_anchor(conn, last_seq, last_hmac)


def _verify_chain_row(
    key: bytes,
    row: sqlite3.Row,
    seq: int,
    expected_seq: int,
    expected_prev: str,
) -> VerifyResult | None:
    """Valida una fila de la cadena (§2.5); devuelve `None` si es correcta o el fallo concreto.

    Comprueba, en orden: (c) contigüidad de `seq`, (b) encadenado por `prev_hmac` y
    (a) recomputación del `entry_hmac` sobre el material canónico. El comportamiento y los
    mensajes son idénticos a los que antes estaban en línea dentro de `verify_chain`.
    """
    # (c) Contigüidad/crecimiento de seq → detecta eliminación intermedia por hueco.
    if seq != expected_seq:
        return VerifyResult(
            ok=False,
            failed_seq=seq,
            reason=(
                f"secuencia no contigua: se esperaba seq={expected_seq} pero se encontró "
                f"seq={seq} (posible eliminación intermedia)"
            ),
        )

    # (b) Encadenado: prev_hmac de esta fila == entry_hmac de la anterior ("" en la génesis).
    if not hmac.compare_digest(row["prev_hmac"], expected_prev):
        return VerifyResult(
            ok=False,
            failed_seq=seq,
            reason=(
                "prev_hmac no coincide con el entry_hmac de la entrada previa "
                "(cadena rota o reordenada)"
            ),
        )

    # (a) Recomputar el entry_hmac sobre el material canónico (payload re-parseado).
    try:
        payload_obj = json.loads(row["payload"]) if row["payload"] else {}
    except (ValueError, TypeError):
        return VerifyResult(
            ok=False,
            failed_seq=seq,
            reason="payload no es JSON válido (contenido manipulado)",
        )
    entry = {
        "event_type": row["event_type"],
        "outcome": row["outcome"],
        "entity_ref": row["entity_ref"],
        "occurred_at": row["occurred_at"],
        "payload": payload_obj,
    }
    recomputed = _compute_entry_hmac(key, expected_prev, entry)
    if not hmac.compare_digest(row["entry_hmac"], recomputed):
        return VerifyResult(
            ok=False,
            failed_seq=seq,
            reason="entry_hmac no coincide con el valor recomputado (contenido manipulado)",
        )

    return None


def _verify_tail_anchor(
    conn: sqlite3.Connection,
    last_seq: int,
    last_hmac: str,
) -> VerifyResult:
    """Valida el ancla de cola (§2.9, R6.6) para detectar truncación del final.

    Comportamiento y mensajes idénticos al bloque que antes cerraba `verify_chain`.
    """
    anchor = conn.execute(
        "SELECT last_seq, last_hmac FROM audit_anchor WHERE id = 1"
    ).fetchone()

    if anchor is None:
        # Sin ancla: si hay entradas, no podemos descartar truncación → fallo explícito.
        # Si la cola está vacía Y no hay ancla, es un estado inicial coherente (cadena vacía ok).
        if last_seq == 0:
            return VerifyResult(ok=True)
        return VerifyResult(
            ok=False,
            failed_seq=last_seq,
            reason="ancla de cola ausente: no se puede descartar truncación del final",
        )

    anchor_seq = int(anchor["last_seq"])
    anchor_hmac = anchor["last_hmac"]

    if anchor_seq != last_seq:
        # El ancla apunta a un seq distinto al último presente → truncación (ancla por delante)
        # o estado incoherente (ancla por detrás).
        return VerifyResult(
            ok=False,
            failed_seq=anchor_seq,
            reason=(
                f"ancla de cola incoherente: last_seq={anchor_seq} pero la última entrada "
                f"presente es seq={last_seq} (posible truncación del final)"
            ),
        )

    if not hmac.compare_digest(anchor_hmac, last_hmac):
        return VerifyResult(
            ok=False,
            failed_seq=last_seq,
            reason="ancla de cola incoherente: last_hmac no coincide con la última entrada",
        )

    return VerifyResult(ok=True)
