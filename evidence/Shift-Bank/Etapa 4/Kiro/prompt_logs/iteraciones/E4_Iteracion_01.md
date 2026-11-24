# E4 — Iteración 01

## Fecha/hora y fase
- Fecha/hora: 2026-11-18 (America/Bogota).
- Fase/milestone: M0 (baseline y evidencia) + M1 (esquema multidivisa, fixture D-02, FX exacto).

## Tareas principales completadas y progreso
- Progreso de tareas principales: **7/31**.
- Completadas en esta iteración: Tareas 1, 2, 3 (M0), 4 (gate G-SPEC aprobado con precondición
  verificada), 5, 6, 7 (M1).
- Nota: los conteos de pruebas (p. ej. 11 pruebas FX) son SUB-pruebas, no tareas principales.

## Actividades y decisiones técnicas
- M0: creación del venv aislado del backend, instalación de dependencias fijadas, ejecución de la
  regresión heredada (backend/Vitest/build) y registro del baseline D1 del NUEVO account.
- Gate T4 (G-SPEC): aprobado por el investigador condicionado a tareas 1–3 completas con
  evidencia; condición verificada antes de continuar.
- T7 (FX): `app/fx.py` con tasas racionales fijas (`fractions.Fraction`) y `ROUND_HALF_UP` una
  sola vez; alineado a la **matriz oficial de la guía** (USD/EUR=9/10, USD/GBP=8/10, EUR/USD=10/9,
  GBP/USD=10/8, EUR/GBP=8/9, GBP/EUR=9/8). Equivalente USD sin redondear para el umbral MFA
  estricto `>1000.00`; redondeado para límites.
- T5 (esquema): extensión aditiva/idempotente/transaccional de `db.migrate` — columnas
  `account.currency/public_id/version` y `transfer.currency`; tablas `domain_event`,
  `account_projection`, `idempotency_key`; índices y triggers append-only de eventos.
- T6 (fixture D-02, DK-01): `seed_stage4` crea CHK-1001 USD 2500.00, SAV-2001 USD 10000.00,
  EUR-3001 EUR 0.00, GBP-4001 GBP 0.00 con `public_id` inmutables, evento `ACCOUNT_OPENED` y
  proyección coherente por cuenta, sin doble conteo; idempotente; no lee ni toca la Etapa 3.
- **Decisión de estrategia de pruebas (Path A, dual-seed) — SEÑALADA al investigador:** para
  preservar el baseline de regresión heredado (AC4-20) y mantener la suite verde en cada paso, el
  arnés heredado usa la siembra COP (`SHIFT_SEED_MODE=legacy` por defecto en `conftest`), mientras
  la app real y las pruebas nuevas usan la fixture D-02 (`SHIFT_SEED_MODE=stage4`,
  `stage4_app_client`). La migración de las pruebas heredadas al modelo multidivisa se hará de
  forma deliberada en los puertos currency-aware (tareas 13–15). No es un cambio de contrato de
  los Specs; es una decisión de arnés reversible. El investigador puede optar por un corte duro
  (Path B) si lo prefiere.

## Archivos creados o modificados
- Modificados: `backend/app/config.py` (monedas, tasas FX, límites/MFA USD), `backend/app/db.py`
  (DDL Etapa 4 en `migrate`), `backend/app/seed.py` (`seed_stage4`), `backend/app/main.py`
  (selección de siembra por `SHIFT_SEED_MODE`), `backend/tests/conftest.py`
  (`SHIFT_SEED_MODE=legacy` por defecto + fixture `stage4_app_client`).
- Creados: `backend/app/fx.py`, `backend/tests/test_fx.py`, `backend/tests/test_schema_stage4.py`,
  `backend/tests/test_fixture_stage4.py`.
- Specs: `tasks.md` y `tasks.meta.json` actualizados (1–7 completas; gate T4 aprobado).

## Pruebas ejecutadas (reales)
- `test_fx.py`: **11 passed**, exit 0.
- `test_schema_stage4.py`: **7 passed**, exit 0.
- Suites de migración (`test_migration.py`, `test_migration_suite.py`, `test_schema_stage2.py`):
  **25 passed**, exit 0.
- `test_fixture_stage4.py`: **4 passed**, exit 0.
- Regresión completa del backend tras M1: **394 passed, 1 warning**, exit 0 (baseline heredado 372
  preservado + 11 FX + 7 schema4 + 4 fixture).
- Baseline M0: backend **372 passed** exit 0; Vitest **3 passed** exit 0; build **41 modules** exit 0.

## Errores, reintentos y correcciones
- Observado y corregido: al introducir la fixture D-02 como siembra única de la app, 78 pruebas de
  API heredadas fallaron (asumen la fixture COP y `kind` en {checking,savings}). Corrección: Path A
  dual-seed (arnés heredado = legacy; app/pruebas nuevas = stage4). Tras la corrección, la suite
  completa volvió a verde (394 passed).
- Ajuste de tasa: la tasa GBP inicial (4/5) se alineó al valor de la guía (8/10, mismo valor
  exacto) y se añadió la verificación de la matriz cruzada completa.
- Entorno: Node v20.17.0/npm 11.6.3 en esta máquina frente a v24.19.0/11.17.0 del baseline de
  preparación; registrado, no ocultado. Resultados de build/Vitest coinciden igualmente.

## Rutas de evidencia
- `_experiment_logs/Kiro/E4/baseline/` (BASELINE-SUMMARY.md, backend/vitest/build logs, pip install,
  environment-versions).
- `_experiment_logs/Kiro/E4/D1/D1-credit-snapshot-stage4.md`.
- Specs: `Kiro/.kiro/specs/shift-bank-stage4/`.

## Interacciones de modelo, llamadas a herramientas, tiempo y créditos
- Modelo: Auto (selección dinámica en servidor). Interacciones/tool-calls/tiempo/créditos exactos
  de esta iteración: **N/D** (no disponibles de forma directa en esta interfaz). D1 PRE del nuevo
  account: 30.24/1000 usados, 969.76 restantes (2026-11-18). No se inventan totales.

## Bloqueadores, limitaciones y próxima actividad
- Bloqueadores: ninguno técnico ahora. Gates pendientes obligatorios: T28 (SonarQube PRE) y T30
  (SonarQube POST) requieren servidor SonarQube y autorización; sin servicio disponible, esas
  tareas FALLAN (no PASS).
- Limitación: "Run All Tasks" nativo es una acción de la UI de Kiro IDE no disponible como
  herramienta en esta sesión; la ejecución se realiza tarea por tarea con evidencia real.
- Próxima actividad: M2 — Tarea 8 (almacén de eventos `app/events.py`), Tarea 9 (proyecciones
  `app/projections.py` + rebuild determinista), Tarea 10 (patrón de comando atómico
  `app/command.py`).
