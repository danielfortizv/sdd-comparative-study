# E2 · Kiro · Sesión de implementación 10 — Tarea 10

- **Fecha:** 2026-11-16
- **Tarea:** 10 — Utilidades compartidas de transacción financiera
- **Objetivo y alcance:** proveer un límite transaccional reutilizable para componer varias
  operaciones de repositorio en una única transacción `BEGIN IMMEDIATE`, como base de las
  futuras operaciones financieras de la Etapa 2. **Solo infraestructura transaccional; sin
  lógica de negocio.**
- **Estado final:** COMPLETED

## Refinamiento de seguimiento T-1

La Tarea 10 se dividió en subtareas 10.1–10.6 (context manager, composición, política de
anidamiento, sin commits ocultos, no alterar `apply_transfer`, verificación), sin reestructurar
las demás tareas ni cambiar el total de 46. Las 6 subtareas quedaron `[x]`.

## Mecanismo financiero heredado inspeccionado

- `repository.apply_transfer`: abre `conn.execute("BEGIN IMMEDIATE")`, aplica débito+crédito+
  estado y `conn.commit()`, con `conn.rollback()` ante excepción. Es el patrón de atomicidad de
  la Etapa 1.
- `db.get_connection`: sqlite3 con `check_same_thread=False`, `row_factory=Row`,
  `PRAGMA foreign_keys=ON`.

## Decisión de ubicación (frontera con `repository.py`)

El `tasks.md` nombraba la Tarea 10 "(`repository.py`)". Para **no alterar `apply_transfer` ni el
comportamiento heredado** (regla explícita de la tarea y condición de las 51 pruebas de
regresión), el helper se implementó en un **módulo nuevo** `app/txn.py` en lugar de modificar
`repository.py`. `repository.py` quedó **sin cambios** (verificado: no aparece en git status).
Esto respeta la instrucción de no refactorizar el comportamiento interno y mantiene el helper
disponible para que las tareas posteriores compongan operaciones de `repository` dentro de una
transacción compartida.

## Utilidades de transacción implementadas (`app/txn.py`)

- `financial_transaction(conn)`: context manager que abre `BEGIN IMMEDIATE` al entrar, `COMMIT`
  si el bloque termina sin excepción y `ROLLBACK` si se propaga una excepción. Sin commits
  intermedios; no usa `executescript`.
- `TransactionError`: se lanza si se intenta abrir una transacción cuando `conn.in_transaction`
  ya es True (no se soportan transacciones anidadas; no se usan savepoints).

### Propiedad / commit / rollback

- **Dueño de la transacción:** el llamador. Todas las operaciones de repositorio dentro del
  `with` usan la misma `conn` → comparten la transacción y se confirman/revierten juntas.
- **Commit** solo al final del bloque sin excepción; **rollback** total ante cualquier excepción
  (incluida `BaseException`), evitando actualizaciones parciales.
- **Anidamiento:** rechazado con `TransactionError` (política documentada).
- **Concurrencia:** `BEGIN IMMEDIATE` adquiere el write-lock al inicio; entre conexiones
  distintas, la segunda recibe `OperationalError: database is locked` hasta el commit de la
  primera (soporte de F8/F9). No se confunde el locking de SQLite (nivel conexión) con la
  idempotencia financiera (nivel aplicación), que se implementará con `UNIQUE` en tareas
  posteriores.

## Comandos ejecutados y resultados reales

1. `python -m pytest tests/test_txn.py -v` → **9 passed in 0.53s** (exit 0).
2. `python -m pytest` (suite completa) → **88 passed, 101 warnings in 5.10s** (exit 0):
   51 (Fase A) + 6 (migración T7) + 12 (esquema T8) + 10 (reloj T9) + 9 (txn T10).
   **Passed 88 · Failed 0 · Skipped 0.**

## Pruebas nuevas (9) y resultados

commit exitoso persiste; rollback ante excepción; atomicidad multi-operación; fallo en 2.ª
operación no preserva la 1.ª (PK duplicada → IntegrityError → rollback); composición de
operaciones de repositorio; sin commits intermedios (invisible a otra conexión hasta el commit);
anidamiento rechazado (`TransactionError`); locking entre conexiones distintas
(`OperationalError` en la 2.ª); funciona con la DB aislada de la app. **Todas PASS.**

## Verificación de regresión

- 51 (Fase A), 18 (migración/esquema), 10 (reloj): todas siguen **verdes** (incluidas en las
  88). No se debilitó, eliminó ni modificó ninguna aserción.

## Verificación de integridad de la BD histórica

- **Antes y después:** `407B0E132E76900FBF59412C31A2D8047A666F2BE1856BE1FF6B88531C89B4A8` —
  sin cambios. `shift_bank.db` no existe en `Etapa 2/Kiro/backend`; sin DB temporales
  residuales. `Etapa 1/Kiro` git limpio.

## Resumen del diff de código

- `app/txn.py`: NUEVO (context manager `financial_transaction` + `TransactionError`). Aditivo.
- `app/repository.py`: **sin cambios** (preservado).
- Ningún otro módulo de aplicación modificado.

## Errores y correcciones

- Ninguno. Las 9 pruebas del helper y las 88 de la suite pasaron en la primera ejecución.

## Métricas

- **Duración de la sesión:** N/D. pytest: 0,53 s (T10) y 5,10 s (suite).
- **Tokens / créditos / interacciones de herramientas:** N/D (no expuestos). No se estiman.

## Archivos creados / modificados

| Acción | Archivo |
|---|---|
| Creado | `Etapa 2/Kiro/backend/app/txn.py` |
| Creado | `Etapa 2/Kiro/backend/tests/test_txn.py` (9 pruebas) |
| Modificado | `Etapa 2/Kiro/.kiro/specs/shift-bank-stage2/tasks.md` (subtareas 10.x + Tarea 10) |
| Creado | `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_10_TAREA_10.md` (este registro) |

## Alcance / restricciones respetadas

- Solo se ejecutó la Tarea 10 (y su refinamiento T-1). Tareas 11–46 sin iniciar y sin marcar;
  Tareas 1–9 preservadas; total de 46 intacto.
- No se implementó configuración/enforcement de límites, ACH/settlement, recurrentes ni
  scheduler; no se tocó el frontend, contratos de API, esquema de BD, requisitos/diseño, la
  Etapa 1 ni registros previos; sin dependencias nuevas; sin estado global mutable, pooling,
  locks distribuidos ni savepoints.
