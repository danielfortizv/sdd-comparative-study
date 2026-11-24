# Tarea 14 — Atomicidad, rechazos y fail-closed de la auditoría (`test_audit_atomicity.py`)

- **Fecha/hora (local):** 2026-11-16T19:31:07
- **Spec:** `.kiro/specs/shift-bank-stage3` (Etapa 3, Opción A)
- **Requisitos:** R5.3, R7.2, R7.3, R7.4 · **Diseño:** §2.7 · **AC:** AC-07, AC-08
- **Entorno:** Windows, Python 3.13.2 (`backend/.venv`), pytest 8.3.4, pytest-cov 7.1.0,
  locust 2.47.0 (solo-dev), anyio 4.16.0.
- **Datos:** DB SQLite temporal y aislada por prueba (fixture `app_client`/`isolated_db_path`).
  NO se tocó la DB histórica ni `SEED-3.md` ni datos de la Etapa 2.

## Objetivo

La Tarea 12 ya auditaba los caminos de ÉXITO (una entrada dentro de la misma
`financial_transaction` que mueve el dinero). La Tarea 14 añade los caminos de **rechazo** que
la 12 dejó fuera y verifica atomicidad/fail-closed de los negativos, sin comprometer ninguna
mutación bancaria.

## Implementación — puntos de emisión de rechazo

Catálogo nuevo en `app/audit.py` (eventos `outcome='rejected'`, payloads NO sensibles):
`EVENT_MFA_FAILED`, `EVENT_INTERNAL_TRANSFER_REJECTED`, `EVENT_ACH_REJECTED`.

| Punto de emisión | Evento | Mecanismo de atomicidad |
|---|---|---|
| `service.confirm_mfa` — PIN inválido (`code != MFA_CODE`) | `MFA_FAILED` | Transacción propia pequeña que SOLO inserta la fila de auditoría (sin débito ni cambio de estado; la transferencia sigue `PENDING_MFA`, reintentable). Tras ello se lanza `INVALID_MFA_CODE` como el flujo heredado. |
| `service.confirm_mfa` — fondos insuficientes al confirmar | `INTERNAL_TRANSFER_REJECTED` | `update_transfer_status_no_commit(... 'FAILED')` (cambio de estado NO financiero, sin saldos) + `append_in_tx` dentro de UNA `financial_transaction`. |
| `service.confirm_mfa` — límite superado (revalidación dentro de la tx) | `INTERNAL_TRANSFER_REJECTED` | La tx financiera ya hizo ROLLBACK (sin débito); el FAILED + rechazo se escriben en UNA tx nueva atómica. |
| `service.create_transfer` — límite superado (revalidación dentro de la tx, ruta inmediata sin MFA) | `INTERNAL_TRANSFER_REJECTED` | Igual que arriba: FAILED (no financiero) + rechazo en UNA `financial_transaction`. |
| `ach_service.confirm_ach_mfa` — PIN inválido | `MFA_FAILED` | Transacción propia pequeña solo-auditoría; la ACH sigue en `pending_auth`, sin débito. |
| `ach_service.confirm_ach_mfa` — fondos/límite al confirmar | `ACH_REJECTED` | La tx financiera ya hizo ROLLBACK (sin débito); `set_ach_status_no_commit(... 'failed')` + rechazo en UNA `financial_transaction`. |

Helper nuevo `repository.update_transfer_status_no_commit` (variante sin commit de
`update_transfer_status`) para componer el cambio de estado FAILED con la auditoría dentro de la
misma transacción. `update_transfer_status` ahora delega en ella + `commit` (comportamiento
heredado intacto).

### Invariantes de diseño respetados (§2.7)

- Una fila de rechazo **nunca** acompaña a una mutación bancaria confirmada: o la tx financiera
  ya revirtió (sin débito) y el rechazo se escribe en su propia tx pequeña, o el cambio
  acompañante es NO financiero (FAILED sin saldos).
- Una mutación bancaria confirmada **siempre** lleva su auditoría de éxito (Tarea 12, intacta).
- No hay doble auditoría: PIN inválido audita solo `MFA_FAILED`; el rechazo por fondos/límite
  audita solo su evento de rechazo.
- PIN inválido NO debita y NO altera el estado heredado (`PENDING_MFA`/`pending_auth`): solo se
  añade la auditoría del intento.

### Mecanismo fail-closed (R7.2)

`txn.financial_transaction` abre `BEGIN IMMEDIATE`, hace COMMIT al salir sin excepción y ROLLBACK
si algo lanza. Como `audit.append_in_tx` se ejecuta DENTRO de esa transacción (sin commit
propio), si la auditoría falla se revierte TODO: el dinero no puede confirmarse sin su auditoría.

## Verificación — `tests/test_audit_atomicity.py` (10 pruebas)

1. `test_exito_commitea_dinero_y_una_auditoria` — éxito atómico: saldo movido + 1 entrada
   `INTERNAL_TRANSFER_COMPLETED`; `verify_chain` ok.
2. `test_fallo_auditoria_revierte_transferencia_interna` — `append_in_tx` parcheado para lanzar
   en una interna COMPLETED → saldos intactos, 0 filas de auditoría, sin COMPLETED espuria.
3. `test_fallo_auditoria_revierte_ach_pending` — igual para creación ACH `pending`: sin débito,
   sin fila ACH, 0 auditoría.
4. `test_pin_invalido_no_debita_y_audita_mfa_failed` — PIN interno erróneo: sin débito, sigue
   `PENDING_MFA`, exactamente 1 `MFA_FAILED` (rejected); `verify_chain` ok.
5. `test_pin_invalido_permite_reintento_exitoso` — tras el fallo, reintento correcto encadena
   `MFA_FAILED` + `MFA_CONFIRMED` + `INTERNAL_TRANSFER_COMPLETED` (3 entradas), cadena íntegra.
6. `test_pin_invalido_ach_no_debita_y_audita_mfa_failed` — PIN ACH erróneo: sin débito, sigue
   `pending_auth`, `MFA_FAILED` presente; sin datos sensibles; cadena ok.
7. `test_rechazo_por_limite_interno_audita_sin_mutacion` — límite superado al confirmar MFA →
   FAILED sin débito + `INTERNAL_TRANSFER_REJECTED`; saldos intactos; cadena ok.
8. `test_rechazo_por_limite_create_transfer_audita_sin_mutacion` — límite diario agotado rechaza
   la segunda interna sin mutación; cadena ok.
9. `test_rechazo_ach_por_limite_al_confirmar_audita_sin_mutacion` — ACH confirmada con límite
   agotado → `failed` sin débito + `ACH_REJECTED`; sin sensibles; cadena ok.
10. `test_secuencia_mixta_mantiene_cadena_y_sin_sensibles` — secuencia éxitos+rechazos: coexisten
    `success` y `rejected`, `verify_chain` ok, ningún payload con cuenta/routing/`enc:`.

## Resultados reales (pytest)

Comando (desde `backend/`, venv):

```
.venv\Scripts\python.exe -m pytest tests/test_audit_atomicity.py -v
```

Salida: **10 passed, 1 warning** (1.03 s). El único warning es un `DeprecationWarning` de
starlette/anyio, preexistente e inocuo.

Regresión completa:

```
.venv\Scripts\python.exe -m pytest -q
```

Salida: **328 passed, 1 warning** (18.85 s).

- Baseline previo documentado: 318 pruebas. 318 + 10 nuevas = **328**. ✔
- Las aserciones de conteo exacto de auditoría de los caminos de ÉXITO en
  `test_audit_integration.py` (Tarea 12) siguen verdes: los eventos de rechazo solo aparecen en
  caminos de rechazo, de modo que las pruebas de solo-éxito no cambian de conteo.

## Veredicto

**PASS.** El dinero no puede confirmarse sin su auditoría (fail-closed), ningún camino de
rechazo commitea una mutación bancaria, el PIN inválido no debita (solo audita el intento), y la
cadena permanece verificable tras secuencias mixtas. Ningún payload de auditoría contiene datos
sensibles.
