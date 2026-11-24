# E2 · Kiro · Sesión de implementación — Lote Fase D (Tareas 19–26)

- **Fecha:** 2026-11-16 · Etapa 2 · Herramienta: Kiro
- **Alcance:** Fase D — beneficiarios y transferencias ACH directas (Tareas 19–26). Autorizado
  solo 19–26; detenerse antes de la Tarea 27.
- **Estado:** T19–T26 todas COMPLETED.

## Resumen por tarea

- **T19** `beneficiaries.py` (validación routing 9 dígitos / cuenta 4–17, enmascarado `••••`+4,
  routing no enmascarado F14) + `ach_repository.py` (CRUD con propiedad del cliente, borrado
  lógico `deleted_at`).
- **T20** `routers/beneficiaries.py`: `GET`/`POST`/`DELETE /api/beneficiaries`.
- **T21** `ach_service.create_ach` (subtareas 21.1–21.5): orden formato→fondos→límites→MFA;
  no sensible → `pending` + débito en una `financial_transaction`; sensible → `pending_auth`
  SIN débito; guardado o ad hoc (con opción de guardar); snapshot de beneficiario.
- **T22** `ach_service.confirm_ach_mfa` + `routers/ach.py` (subtareas 22.1–22.3): `POST /api/ach`
  y `/ach/{ref}/mfa`; MFA correcta → `pending_auth → pending` + débito en una transacción;
  incorrecto → 401 (reintento); expiración → `expired` sin débito; fondos/límite al confirmar →
  `failed` sin débito.
- **T23** `ach_service.settle_ach`: `pending → settled` idempotente (guarda `WHERE
  status='pending'`), sin re-débito; elegibilidad determinista por retardo
  `ACH_SETTLEMENT_DELAY_SECONDS` con reloj inyectable. **Disparo autónomo = Tarea 32** (T-6).
- **T24** `ach_service.fail_ach`: `pending → failed` + reembolso exactamente-una-vez (guarda
  `refunded=0`); idempotente.
- **T25** historial unificado en `routers/transfers.py` (`GET /api/transfers`): campo aditivo
  `type` ('internal'|'ach'); internas conservan `direction {from,to}` y estados MAYÚSCULAS; ACH
  añaden `beneficiary` (enmascarado) y estados minúsculas. Sin exponer número de cuenta completo.
- **T26** `tests/test_ach.py` (16 pruebas).

## Punto 5 — Inspección del gap de atomicidad del flujo interno

**Confirmado el gap reportado en la Fase C:** `repository.create_transfer` hace `conn.commit()`
tras el INSERT, antes de la `financial_transaction` que aplica el débito (camino interno
COMPLETED). Consecuencia real: si el proceso cayera entre ambos, quedaría una fila interna
transitoria en estado `PENDING_MFA` **sin** `reference` y **sin** débito. **No** es un débito
perdido ni un doble débito ni un saldo inconsistente (la fila no es financieramente activa; no
es confirmable). Es una creación-de-fila separada del efecto financiero, de bajo impacto.

**No se reprodujo en ACH:** `ach_repository.create_ach_no_commit` + `debit_source_no_commit`
se componen DENTRO de una sola `financial_transaction`, de modo que la fila ACH `pending` y su
débito se commitean juntos — nunca una ACH `pending` sin débito (punto 4). No se rediseñó el
flujo interno (fuera del alcance 19–26); el gap queda documentado como riesgo conocido de bajo
impacto para una posible mejora futura.

## Punto 6 — Dependencia del scheduler (T-6)

La **lógica** de settlement (`settle_ach`) y de fallo (`fail_ach`) está implementada y probada
con reloj inyectable. Su **disparo autónomo** depende del scheduler de fondo de la **Tarea 32**,
que NO se implementó aquí. El settlement/fallo NO es autónomamente operativo todavía: hoy solo
es invocable por la lógica/pruebas. Documentado, sin implementar la Tarea 32.

## Punto 7 — Compatibilidad del historial (T25) y actualización de aserciones

El historial unificado añade el campo aditivo `type`. Esto obligó a actualizar **solo** las
aserciones estrictas incompatibles del checkpoint de Fase A (que exigían "exactamente los 5
campos" o "sin `type`"), preservando el resto:
- `test_regression_api_contracts.py::test_historial_estructura_y_campos` → admite `type`.
- `test_regression_api_contracts.py::test_internas_conservan_forma_sin_beneficiario` (renombrado
  de `test_internas_no_tienen_campos_ach`) → internas con `type='internal'`, sin `beneficiary`,
  con `direction`.
- `test_regression_internal_transfers.py::test_estructura_e_estados_del_historial_heredados`.
- `test_regression_mfa.py::test_estado_y_forma_tras_completar`.
Las cuatro conservan la verificación de los campos y valores HEREDADOS; solo admiten el añadido
aprobado `type`. No se debilitó ninguna otra aserción.

## Archivos creados / modificados

| Acción | Archivo |
|---|---|
| Creado | `backend/app/beneficiaries.py` |
| Creado | `backend/app/ach_repository.py` |
| Creado | `backend/app/ach_service.py` |
| Creado | `backend/app/routers/beneficiaries.py` |
| Creado | `backend/app/routers/ach.py` |
| Modificado | `backend/app/routers/transfers.py` (historial unificado, T25) |
| Modificado | `backend/app/main.py` (registro de routers ach/beneficiaries) |
| Creado | `backend/tests/test_ach.py` (16 pruebas) |
| Modificado | `backend/tests/test_regression_api_contracts.py` (2 aserciones, T25) |
| Modificado | `backend/tests/test_regression_internal_transfers.py` (1 aserción, T25) |
| Modificado | `backend/tests/test_regression_mfa.py` (1 aserción, T25) |
| Modificado | `.kiro/specs/shift-bank-stage2/tasks.md` (Tareas 19–26 + subtareas 21/22) |
| Creado | `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_19-26_FASE_D.md` |

## Comandos y resultados reales

1. `python -m pytest tests/test_ach.py` → **16 passed** (exit 0).
2. `python -m pytest` (suite completa, checkpoint regresión) → **122 passed, 0 failed, 0
   skipped, 1 warning in 7.34s** (exit 0): 51 (Fase A) + 6 (T7) + 12 (T8) + 10 (T9) + 9 (T10) +
   7 (lote B) + 11 (Fase C) + 16 (Fase D).

## Errores y correcciones (iteraciones)

1. **Bug real: alias `from` faltante en `CreateAchRequest`.** El request enviaba `"from":
   "savings"` pero el modelo usaba el default `"checking"` (sin `Field(alias="from")`), de modo
   que el débito ACH se aplicaba a la cuenta equivocada y el saldo esperado no cuadraba (3 tests
   fallaban). **Corrección:** `from_: str = Field(default="checking", alias="from")`, igual que
   el `CreateTransferRequest` heredado. Detectado por los tests; verificado por depuración
   directa (débito correcto en aislamiento vs incorrecto vía API).
2. **Aserciones estrictas incompatibles con `type`** (2 adicionales a las de T25): corregidas
   como adaptación aprobada (ver punto 7), sin debilitar la verificación heredada.

No se debilitó ni eliminó ninguna aserción de baseline para "hacer pasar" la suite; el bug 1 era
de implementación y se corrigió en el código.

## Estado de regresión de la Etapa 1

Las 51 pruebas de la Fase A siguen verdes (dentro de las 122). El contrato de internas conserva
sus valores heredados; el único cambio observable es el campo aditivo `type`, aprobado (D03/D05).

## Riesgos / dependencias abiertas

- **Scheduler (Tarea 32):** settlement y fallo ACH no se disparan autónomamente aún (T-6).
- **Gap de atomicidad interno (bajo impacto):** documentado; no reproducido en ACH; posible
  mejora futura fuera del alcance 19–26.
- Sin otros blockers ni contradicciones de diseño.

## Integridad de la base de datos histórica

- SHA-256 `407B0E132E76900FBF59412C31A2D8047A666F2BE1856BE1FF6B88531C89B4A8` — sin cambios.
- `shift_bank.db` no existe en `Etapa 2/Kiro/backend`; sin DB temporales residuales; `Etapa 1/
  Kiro` git limpio.

## Métricas

- **Duración:** N/D. pytest: 1,48 s (Fase D) y 7,34 s (suite).
- **Tokens / créditos / interacciones:** N/D (no expuestos). No se estiman.

## Alcance / restricciones

- Solo Tareas 19–26. Tareas 27–46 sin iniciar; Tareas 1–18 preservadas; total de 46 intacto.
- No se implementó recurrentes ni el scheduler (Fase E / Tarea 32). No se tocó el frontend, la
  Etapa 1 ni registros previos; sin dependencias nuevas.
