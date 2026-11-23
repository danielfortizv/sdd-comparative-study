# E2 · Kiro · Registro 05 — Refinamiento de design.md tras auditoría

- **Fecha:** 2026-11-16 · Etapa 2 · Herramienta: Kiro
- **Fase:** refinamiento del diseño tras auditoría (previa a tasks.md)
- **Autorización:** el investigador aprobó corregir los hallazgos HIGH, MEDIUM y los LOW
  relevantes, y la decisión E2-KIRO-D07. Autorizado a modificar solo `design.md` y la
  documentación experimental asociada.

> Este registro NO sobrescribe la evidencia histórica. El diseño original (Registro 04) y los
> hallazgos de auditoría previos se conservan. El primer diseño **no** estaba libre de defectos;
> este registro documenta su corrección.

## Trazabilidad de versiones de design.md

| Versión | SHA-256 | Líneas | Bytes |
|---|---|---|---|
| v1 (Registro 04) | `AB53F2C83F042B6665F9BE4922284A59790E35BD2231ED06615F72719CB1ED93` | 512 | 32.435 |
| v2 (este registro) | `FA8F38DFC7DF6E8B6182F7B9ED67ED7A6A5AF724D9B652587EF7A0AC41A5BB26` | 718 | 48.320 |

## Decisión registrada

- **E2-KIRO-D07** — modelo operativo de un solo worker/scheduler; la idempotencia financiera
  reside en el modelo de datos (UNIQUE + transacción), no en el número de procesos. D01–D06
  preservadas.

## Resolución de hallazgos de auditoría

### HIGH

- **F10 (idempotencia durable de ejecuciones recurrentes):** RESUELTO. Nueva tabla
  `schedule_execution` con `UNIQUE(schedule_id, due_at)`; identidad estable `(schedule_id,
  due_at original)`; INSERT de ejecución + revalidación + movimiento + débito + avance de
  `next_run_at` en **una** transacción `BEGIN IMMEDIATE`; crash antes de COMMIT → ROLLBACK total;
  COMMIT exitoso → reintento falla el INSERT (sin repetir efecto). DD-7 añadida.
- **F10-bis (modelo de worker):** RESUELTO. Subsección "Modelo de worker": arranque de un único
  scheduler en `lifespan`, apagado limpio, recuperación tras reinicio, protección por restricción
  durable (no por el nº de procesos), y justificación de por qué multi-worker queda fuera del
  alcance (D07) con la limitación operativa futura documentada.

### MEDIUM

- **F7 (ACH creación+débito atómicos):** RESUELTO. "Transacción financiera única de activación
  ACH": revalidación + crear/finalizar fila + débito + `status='pending'` + persistencia en una
  sola transacción; nunca se commitea `pending` sin débito; fallo antes de COMMIT sin efecto
  parcial.
- **F8/F9 (límites atómicos y concurrencia):** RESUELTO. Los pasos leer saldo → leer límites →
  calcular consumo diario → validar → debitar ocurren **dentro de la misma** transacción
  `BEGIN IMMEDIATE` (interna, ACH y recurrente); el check previo no es autoritativo. Explicación
  de por qué la serialización de escritor único de SQLite + lectura intra-transacción elimina la
  ventana TOCTOU.
- **F11 (migración transaccional):** RESUELTO. `migrate()` en una única transacción con ROLLBACK
  ante fallo; orden esquema→índices→ALTER→backfill→seed; idempotente; testable sobre copia de DB
  de E1 sin tocar la original.
- **F12 (tipo de transferencia heredada):** RESUELTO. Columna `type TEXT NOT NULL DEFAULT
  'internal'` + backfill de robustez; los consumidores nunca interpretan heredadas como ACH ni
  como tipo desconocido.

### LOW (relevantes, abordados)

- **F3 (ACH esperando MFA):** RESUELTO. Estado explícito `pending_auth` (no financiero, sin
  débito, no cuenta para límites), distinto del `pending` activo; expira a `expired` sin débito.
- **F13 (integridad de BD):** RESUELTO. Documentadas FKs, unicidad (`UNIQUE(schedule_id,
  due_at)`) e índices (`transfer(created_at)`, `transfer(type,status)`, `recurring_schedule
  (status,next_run_at)`, `beneficiary(customer_id,deleted_at)`).
- **UI-1 (compat. frontend):** RESUELTO. `STATUS_LABEL` extendido con etiquetas ACH;
  `TransferHistoryItem` con `direction` opcional + `type` + `beneficiary?`; renderizado
  condicional por `type`; internas conservan `direction` intacto.
- **Startup hook:** RESUELTO. Migración de `@app.on_event("startup")` a `lifespan` con orden
  `init_schema → migrate → seed → lanzar scheduler`; siembra idempotente, sin duplicar/omitir.
- **Beneficiary snapshot:** RESUELTO. Campos del snapshot (`name`, `bank`, `routing_number`,
  `account_number`) y su relación con el enmascarado (persiste completo, API solo `account_masked`).
- **F14 (routing):** RESUELTO. Política explícita: el routing (público, no secreto) no se
  enmascara; solo se enmascara el número de cuenta (D05); sin seguridad ajena al contrato.

## Verificación

- Cobertura R1–R16: mantenida; R10/R11/R14 pasan de PARTIAL a COVERED con los fixes.
- Consistencia con D01–D07: verificada (D07 incorporada en §scheduler y §idempotencia).
- Atomicidad de efectos financieros y avance de ocurrencias: garantizada por transacción única +
  UNIQUE durable (F7, F8/F9, F10).
- Sin hallazgos CRITICAL/HIGH/MEDIUM restantes conocidos a nivel de diseño.
- `requirements.md` sin cambios (SHA-256 `D75CDB69…` idéntico). E1 intacta.

## Integridad

- Modificado: `design.md`. No se tocó `requirements.md`, specs de E1, código, pruebas, seed ni
  contrato. No se generó `tasks.md`.
- Evidencia previa (Registros 01–04, D01–D06, auditoría) preservada; D07 añadida.

## Aclaración importante

No se ha validado el diseño mediante ejecución: no se ha implementado código. Las garantías
descritas (atomicidad, exactamente-una-vez) son propiedades **de diseño**, a verificar con
pruebas en la fase de implementación.
