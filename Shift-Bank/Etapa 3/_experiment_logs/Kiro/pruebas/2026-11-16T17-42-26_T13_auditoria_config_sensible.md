# Tarea 13 — Auditoría de eventos de configuración sensible

- **Fecha:** 2026-11-16T17:42:26 (hora local de la máquina)
- **Milestone:** M2 (Auditoría transaccional, integridad y concurrencia)
- **Requisitos:** R5.2 (auditar acciones de configuración sensible atómicas con su cambio),
  R5.5 (las consultas de solo lectura NO generan auditoría)
- **Diseño:** §2.7 (atomicidad, eventos no financieros), §5.2 (catálogo de eventos, payload no sensible)
- **AC:** AC-05
- **Entorno:** Windows, Python 3.13.2, venv `backend/.venv`, pytest 8.3.4

## Alcance implementado

Se auditan tres familias de acciones de configuración/administración, cada una atómica con su
propio cambio (misma `financial_transaction`), sin auditar ninguna lectura:

1. Alta/baja de beneficiario (`POST`/`DELETE /api/beneficiaries`).
2. Actualización de límites (`limit_service.update_limits`).
3. Ciclo de vida de schedule recurrente (pausar / reanudar / cancelar).

## Constantes de catálogo añadidas (`app/audit.py`)

Se extendió el catálogo `EVENT_*` (Tarea 12) con los eventos de configuración de §5.2:

- `EVENT_BENEFICIARY_CREATED = "BENEFICIARY_CREATED"`
- `EVENT_BENEFICIARY_DELETED = "BENEFICIARY_DELETED"`
- `EVENT_LIMIT_UPDATED = "LIMIT_UPDATED"`
- `EVENT_SCHEDULE_PAUSED = "SCHEDULE_PAUSED"`
- `EVENT_SCHEDULE_RESUMED = "SCHEDULE_RESUMED"`
- `EVENT_SCHEDULE_CANCELLED = "SCHEDULE_CANCELLED"`

(Resultado `OUTCOME_SUCCESS` para todas; son éxitos de configuración.)

## Puntos de emisión y cómo se mantuvo la atomicidad (refactors no-commit)

Cada operación emisora commiteaba antes por su propia vía; se restructuró para que la mutación +
el `append_in_tx` ocurran en UNA sola `financial_transaction` (que posee el commit). Para no
romper otros llamadores de helpers de repositorio compartidos, se añadieron variantes
`*_no_commit` y se conservó la versión committing original delegando en la de no-commit.

| Acción | Emisión | Refactor de atomicidad | entity_ref | payload (no sensible) |
|--------|---------|------------------------|------------|-----------------------|
| Alta beneficiario | `routers/beneficiaries.create_beneficiary` | nuevo `ach_repository.create_beneficiary_no_commit` + `append` en `financial_transaction`; la `create_beneficiary` committing se conserva (delega en la no-commit) | `beneficiary:<uuid>` | `{bank, account_masked}` (últimos 4) |
| Baja beneficiario | `routers/beneficiaries.delete_beneficiary` | nuevo `ach_repository.soft_delete_beneficiary_no_commit` + `append` en `financial_transaction`; audita SOLO si la baja transiciona | `beneficiary:<uuid>` | `{bank, account_masked}` |
| Actualización de límites | `limit_service.update_limits` | se eliminó el `conn.commit()` interno; nuevo `_upsert_limits_no_commit` + `append` en `financial_transaction` (la validación de entrada ocurre ANTES, sin abrir tx) | `limits:<customer_id>` | `{per_transfer_cents, daily_cents}` |
| Pausar schedule | `recurring_service.pause_schedule` | nuevo `repository.update_schedule_status_no_commit` + `append` en `financial_transaction`; la `update_schedule_status` committing se conserva (delega en la no-commit) | `schedule:<id>` | `{status, frequency}` |
| Reanudar schedule | `recurring_service.resume_schedule` | igual; `occurred_at` usa el `now` inyectable; recalcula `next_run_at` en la misma tx | `schedule:<id>` | `{status, frequency}` |
| Cancelar schedule | `recurring_service.cancel_schedule` | igual | `schedule:<id>` | `{status, frequency}` |

**Fail-closed (R7.2):** como `append_in_tx` no commitea (lo hace el context manager), si el
`append` lanza, el `financial_transaction` hace ROLLBACK y la mutación de configuración no
persiste.

## Decisión sobre `save_adhoc` (evitar transacción anidada)

`ach_service.create_ach` (ruta `save_adhoc`) también crea un beneficiario vía
`create_beneficiary`. Esa llamada ocurre **antes** de abrir la `financial_transaction` de la ACH
(no hay anidamiento), por lo que la variante committing sigue siendo correcta allí.

**Decisión documentada:** `BENEFICIARY_CREATED` se emite **solo** en la ruta explícita
`POST /api/beneficiaries`. En `save_adhoc` el evento `ACH_*` (ya emitido por la Tarea 12) cubre
la operación; no se duplica un evento de beneficiario ni se abre una transacción dentro de la
transacción ACH (evita `TransactionError` por anidamiento). No se observó ningún error de
transacción anidada en la suite completa.

## R5.5 — Lecturas sin auditoría

`GET /api/beneficiaries`, `GET /api/limits`, `GET /api/recurring` y `GET /api/transfers`
(historial) no emiten ninguna entrada. Verificado en `test_lecturas_no_generan_auditoria`.

## Pruebas añadidas — `tests/test_audit_config_events.py` (11 pruebas)

- `test_beneficiary_created_emite_una_entrada` — 1 entrada `BENEFICIARY_CREATED`, payload no sensible, cadena íntegra.
- `test_beneficiary_deleted_emite_una_entrada` — 1 entrada `BENEFICIARY_DELETED`.
- `test_beneficiary_delete_inexistente_no_audita` — 404 sin auditoría.
- `test_limit_updated_emite_una_entrada` — 1 entrada `LIMIT_UPDATED` con los límites en centavos.
- `test_limit_update_invalido_no_audita_ni_cambia` — entrada inválida → sin auditoría ni cambio.
- `test_schedule_pause_resume_cancel_emiten_una_cada_uno` — 3 entradas en orden; `entity_ref=schedule:<id>`.
- `test_schedule_transicion_ilegal_no_audita` — transición ilegal no audita.
- `test_lecturas_no_generan_auditoria` — R5.5.
- `test_rollback_beneficiario_si_falla_auditoria` — rollback (monkeypatch de `append_in_tx`): sin beneficiario ni auditoría.
- `test_rollback_limite_si_falla_auditoria` — rollback: límites sin cambio.
- `test_rollback_schedule_si_falla_auditoria` — rollback: schedule sigue `active`.

Payloads verificados sin cuenta/routing en claro ni tokens `enc:`; `verify_chain` íntegra tras
las emisiones.

## Resultados reales de pytest

Comando: `python -m pytest tests/test_audit_config_events.py -v`

```
11 passed, 1 warning in 1.10s
```

Comando: `python -m pytest -q` (suite completa)

```
318 passed, 1 warning in 16.92s
```

- Baseline previo: **307** pruebas.
- Nuevas: **11**.
- Total: **318** → 307 + 11, sin regresiones y sin errores de transacción anidada.

## Preservación

No se modificó `SEED-3.md` ni ningún dato histórico de la Etapa 2. Todas las pruebas usan DB
SQLite temporal aislada por prueba (fixtures `isolated_db_path`/`app_client`).

## Veredicto

**PASS** — atomicidad y rollback demostrados para beneficiario, límite y schedule; lecturas sin
auditoría; payloads no sensibles; cadena verificable; sin nested-tx; suite completa verde (318).
