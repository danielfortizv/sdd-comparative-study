# Tarea 12 — Integración transaccional de auditoría en operaciones financieras

- **Fecha/hora (local):** 2026-11-16 17:23:05
- **Milestone:** M2 (Auditoría transaccional, integridad y concurrencia)
- **Requisitos:** R5.1, R7.1, R7.5 · **Diseño:** §2.3, §2.7, §5.2 · **AC:** AC-05, AC-07
- **Entorno:** Windows, Python 3.13.2 (`backend/.venv`), pytest 8.3.4
- **Datos históricos / `SEED-3.md`:** NO modificados. Todas las pruebas usan DB SQLite temporal
  aislada por test (fixture `isolated_db_path`).

## Objetivo

Emitir exactamente UNA entrada de auditoría por transición de estado financiero, DENTRO de la
MISMA `financial_transaction` (`BEGIN IMMEDIATE`) que aplica el cambio de dinero/estado, de modo
que dinero + auditoría se confirmen atómicamente (R7.1) y se reviertan juntos ante fallo. Se usa
`audit.append_in_tx` (Tarea 10), que NO hace commit: escribe en la transacción ya abierta por el
servicio llamador.

## Cómo se evita el anidamiento de transacciones

`txn.financial_transaction` lanza `TransactionError` si la conexión ya está en transacción
(`conn.in_transaction`). Por eso la auditoría NUNCA abre una transacción propia: cada
`audit.append_in_tx(conn, ...)` se coloca **dentro** del bloque `with financial_transaction(conn):`
que ya está abierto por la operación financiera, antes del COMMIT implícito del context manager.
No se usan helpers de repositorio que hagan su propio commit para la escritura de auditoría.

## Puntos de emisión (catálogo §5.2)

Catálogo de constantes centralizado en `app/audit.py` (`EVENT_*`, `OUTCOME_*`) para un único
origen de verdad de literales.

### `app/service.py`

| Punto | event_type | outcome | entity_ref | payload (claves) |
|-------|-----------|---------|-----------|------------------|
| `create_transfer` (ruta inmediata, sin MFA), dentro del `with financial_transaction` que llama a `apply_transfer_in_tx` | `INTERNAL_TRANSFER_COMPLETED` | `success` | `internal:<transfer.id>` | `amount_cents, from_kind, to_kind, status="COMPLETED", mfa=false` |
| `confirm_mfa` (éxito), dentro del `with financial_transaction` | `MFA_CONFIRMED` | `success` | `reference` (o `internal:<id>`) | `amount_cents, from_kind, to_kind, channel="internal"` |
| `confirm_mfa` (éxito), mismo bloque | `INTERNAL_TRANSFER_COMPLETED` | `success` | `reference` (o `internal:<id>`) | `amount_cents, from_kind, to_kind, status="COMPLETED", mfa=true` |

Enfoque documentado para MFA: se emiten DOS eventos de éxito encadenados (`MFA_CONFIRMED` →
`INTERNAL_TRANSFER_COMPLETED`), ambos dentro de la misma transacción que aplica el débito.

### `app/ach_service.py`

| Punto | event_type | outcome | entity_ref | payload (claves) |
|-------|-----------|---------|-----------|------------------|
| `create_ach` ruta no sensible `pending` + débito | `ACH_PENDING` | `success` | `ach:<reference>` | `amount_cents, from_kind, status="pending", channel="ach"` |
| `create_ach` ruta sensible `pending_auth` (sin débito) | `ACH_PENDING_AUTH` | `success` | `ach:<reference>` | `amount_cents, from_kind, status="pending_auth", channel="ach"` |
| `confirm_ach_mfa` éxito (pending_auth→pending + débito) | `ACH_CONFIRMED` | `success` | `ach:<reference>` | `amount_cents, from_kind, status="pending", channel="ach", mfa=true` |
| `settle_ach` solo si `affected==1` (transición real) | `ACH_SETTLED` | `success` | `ach:<reference>` | `amount_cents, from_kind, status="settled", channel="ach"` |
| `fail_ach` solo si `affected==1` (reembolso 1-vez) | `ACH_FAILED_REFUNDED` | `success` | `ach:<reference>` | `amount_cents, from_kind, status="failed", refunded=true, channel="ach"` |

`settle_ach`/`fail_ach`: la comprobación `affected == 1` y la append se hacen DENTRO del mismo
`with financial_transaction`, de modo que un settle/fail idempotente que no transiciona NO deja
auditoría.

### `app/recurring_service.py`

| Punto | event_type | outcome | entity_ref | payload (claves) |
|-------|-----------|---------|-----------|------------------|
| `_process_one`, `business_ok` (éxito de ocurrencia) | `RECURRING_EXECUTED` | `success` | `schedule:<schedule.id>` | `amount_cents, type, frequency, from_kind, status="executed"` |
| `_process_one`, rama fallida (fondos/límite) | `RECURRING_FAILED` | `rejected` | `schedule:<schedule.id>` | `amount_cents, type, frequency, from_kind, status="failed"` |

La append se escribe DESPUÉS del `INSERT` en `schedule_execution` y del avance de `next_run_at`,
todo dentro de la misma transacción. Si la ocurrencia ya estaba registrada, el `INSERT` en
`schedule_execution` lanza `IntegrityError` (colisión `UNIQUE(schedule_id, due_at)`) ANTES de la
append, por lo que una ocurrencia OMITIDA (`skipped`) revierte toda la transacción y NO deja fila
de auditoría. Idempotencia exactamente-una-vez intacta.

## Restricciones de contenido (R5.6)

- Los payloads contienen SOLO metadatos no sensibles: `amount_cents` (centavos), `from_kind`/
  `to_kind` (kinds de cuenta), `status`, `frequency`, `type`, `channel`, flag `mfa`/`refunded`.
- `entity_ref` es una referencia pública: `reference` (uuid ya expuesto por la API), `ach:<ref>`,
  `internal:<id>` (uuid opaco de transferencia) o `schedule:<id>` (uuid de schedule, ya usado en
  la API). Nunca PII ni rowids internos más allá de lo ya expuesto.
- Verificado por `test_audit_integration._assert_no_sensitive_digits`: ningún payload contiene la
  cuenta (`9876543210`) ni el routing (`123456789`) del beneficiario de prueba, ni tokens
  `enc:v1:` crudos.

## Pruebas añadidas

`tests/test_audit_integration.py` (9 pruebas): una entrada por transición en interna COMPLETED,
interna MFA (MFA_CONFIRMED + COMPLETED), ACH pending/pending_auth/confirm/settle/fail, ejecución
recurrente; duplicado recurrente (`skipped`) sin auditoría; `verify_chain` ok en todos; conteo de
auditoría == nº de transiciones; payloads sin dígitos sensibles.

## Resultados reales (pytest)

### Archivo nuevo

```
$ .venv\Scripts\python.exe -m pytest tests/test_audit_integration.py -v
...
9 passed, 1 warning in 1.38s
```

### Suite completa

```
$ .venv\Scripts\python.exe -m pytest -q
307 passed, 1 warning in 16.14s
```

### Verificación del delta (298 heredadas + 9 nuevas = 307)

```
$ .venv\Scripts\python.exe -m pytest -q --ignore=tests/test_audit_integration.py
298 passed, 1 warning in 15.76s
```

## Veredicto

**PASS.** Se emite exactamente una entrada de auditoría por transición financiera dentro de la
misma `financial_transaction`; no hay anidamiento (sin `TransactionError`); el duplicado
recurrente `skipped` no deja fila de auditoría; `verify_chain` íntegra; las 298 pruebas heredadas
siguen verdes (auditoría aditiva en la misma transacción) y las 9 nuevas pasan (307 total).
