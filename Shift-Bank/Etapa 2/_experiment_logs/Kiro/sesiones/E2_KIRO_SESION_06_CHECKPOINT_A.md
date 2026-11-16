# E2 · Kiro · Sesión 06 — Checkpoint A: Línea base de regresión de la Etapa 1

- **Fecha:** 2026-11-16
- **Tarea:** 6 — Checkpoint A: registrar la línea base de regresión (cierre de la Fase A)
- **Propósito:** fijar oficialmente el baseline de regresión de la Etapa 1 **antes** de iniciar
  migraciones de BD y funcionalidad nueva (Fase B en adelante).
- **Estado del checkpoint:** **PASS**
- **Estado de la Tarea 6:** COMPLETED

## Tareas de la Fase A completadas

| Tarea | Descripción | Pruebas |
|---|---|---|
| 1 | Arnés de pruebas + DB aislada | 4 |
| 2 | Regresión: cuentas y saldos iniciales | 8 |
| 3 | Regresión: transferencias internas (sin MFA) | 12 |
| 4 | Regresión: MFA heredada | 14 |
| 5 | Regresión: contratos de API e historial | 13 |
| **6** | **Checkpoint A (este registro)** | — |

## Resultado final de la suite (reproducible)

- **Comando:** `python -m pytest` (desde `Etapa 2/Kiro/backend`, con `backend/.venv`).
- **Recolectadas:** 51 · **Passed: 51** · **Failed: 0** · **Skipped: 0** · **Warnings: 101**.
- **Duración:** 2,84 s. · **Exit code:** 0.

### Inventario de pruebas por categoría

| Archivo | Categoría | Pruebas |
|---|---|---|
| `tests/test_harness.py` | arnés / aislamiento | 4 |
| `tests/test_regression_accounts.py` | cuentas y saldos | 8 |
| `tests/test_regression_internal_transfers.py` | transferencias internas | 12 |
| `tests/test_regression_mfa.py` | MFA heredada | 14 |
| `tests/test_regression_api_contracts.py` | contratos de API e historial | 13 |
| **Total** | | **51** |

Comandos de verificación reproducibles:
- Suite completa: `python -m pytest`
- Por categoría: `python -m pytest tests/<archivo>.py -v`

## Revisión del repositorio e integridad

- **Rama Git:** `ShiftBank`.
- **Commit (HEAD) al cierre:** `da4209dc3ea9eda08f13de08abe29800bcdf6513`.
  - Nota: al inicio de la secuencia de implementación el HEAD era
    `ebf1017748928b30a9a5ad68a56b9b532f304e86`. El repositorio (monorepo del estudio) avanzó por
    actividad externa a esta tarea; **`Etapa 1/Kiro` permanece en git limpio** (sin cambios), que
    es la condición relevante para la integridad del baseline.
- **`git status` de `Etapa 1/Kiro`:** vacío (sin cambios), antes y después.

### Hashes relevantes (SHA-256)

- **DB histórica `Etapa 1/Kiro/backend/shift_bank.db`:**
  `407B0E132E76900FBF59412C31A2D8047A666F2BE1856BE1FF6B88531C89B4A8` (36 864 bytes).
- **Fuentes heredadas del backend (`backend/app/*.py`) en la copia de E2:** inventariadas en
  `preparacion/E2_KIRO_CHECKPOINT_A_APP_SHA256.csv` (12 archivos).

### Verificación de no modificación funcional del código heredado

- Se compararon los 12 archivos `backend/app/*` de la copia de E2 contra el baseline de
  preparación (`E2_KIRO_INITIAL_COPY_SHA256.csv`, generado tras la copia inicial):
  **0 discrepancias** → las fuentes heredadas son **idénticas bit a bit** al baseline. El código
  de aplicación heredado NO fue modificado funcionalmente; la Fase A solo añadió `tests/` y
  artefactos de prueba (`requirements-dev.txt`, `pytest.ini`), sin tocar `app/`.
- Esta verificación usa **SHA-256**, no timestamps ni tamaños.

## Integridad de la base de datos histórica

- `shift_bank.db` histórica: hash y tamaño sin cambios; nunca fue abierta por las pruebas (los
  fixtures usan DB temporales aisladas).
- Registros sembrados y saldos preservados: verificado funcionalmente por las pruebas de las
  Tareas 2–5 (Checking 5.000.000,00; Savings 15.000.000,00; 2 históricas COMPLETED), todas sobre
  DB temporales que reproducen la siembra sin tocar la histórica.
- **Sin DB temporales residuales** tras la ejecución; **no** existe `shift_bank.db` en
  `Etapa 2/Kiro/backend`.

## Consideración de compatibilidad futura — campo `type` (historial unificado)

Las pruebas estrictas de la Tarea 5 (`test_regression_api_contracts.py`) afirman que cada
entrada de historial de internas contiene **exactamente** `{date, direction, amount,
description, status}` y **no** contiene el futuro campo `type` (ni `beneficiary`).

La decisión aprobada **E2-KIRO-D03** requiere que el historial unificado distinga `internal` de
`ach`, lo que en el diseño (D05) se implementa **añadiendo** un campo `type` a cada entrada
(extensión aditiva). Esto crea un **conflicto potencial** entre:

- la aserción histórica estricta "no debe existir `type`" (Tarea 5), y
- la extensión aditiva aprobada de la Etapa 2 (D03/D05).

**Análisis y distinción (sin modificar nada ahora):**

1. Lo que el baseline debe **preservar** es el **valor y comportamiento de los campos
   heredados** de una transferencia interna: `direction {from,to}` con nombres amigables,
   estados en MAYÚSCULAS, `amount` decimal-string, ausencia de identificadores internos y de
   saldo resultante. Eso es la compatibilidad hacia atrás real (HER-01, D05).
2. Añadir un campo **nuevo y opcional** (`type`) a la respuesta **no** altera esos valores
   heredados: es una extensión aditiva. Prohibir un campo aditivo explícitamente aprobado NO es
   una regresión funcional; es una aserción demasiado estricta del test de baseline.
3. Por tanto, la aserción `test_internas_no_tienen_campos_ach` (y la de "campos exactos" en
   `test_historial_estructura_y_campos`) es un **invariante de snapshot del baseline de la Etapa
   1**, correcto para fijar el punto de partida, pero que **deberá ajustarse en la tarea de
   implementación del historial unificado** (Tarea 25) para volverse "Stage 2-aware":
   seguir verificando que los campos heredados conservan su valor/forma, pero permitir el campo
   aditivo `type` (y `beneficiary` solo en entradas ACH).

**Pruebas futuras que requerirán aserciones conscientes de la Etapa 2:**
- `test_regression_api_contracts.py::test_internas_no_tienen_campos_ach` → relajar la prohibición
  de `type`; mantener la ausencia de `beneficiary` **en entradas internas**.
- `test_regression_api_contracts.py::test_historial_estructura_y_campos` → cambiar "conjunto
  exacto de 5 campos" por "los 5 campos heredados presentes y con su forma, más campos aditivos
  permitidos".

**Propuesta para preservar evidencia histórica permitiendo la extensión aditiva (a ejecutar en
su momento, con autorización):**
- Conservar este checkpoint y las pruebas de la Fase A **sin modificar** como evidencia del
  baseline de la Etapa 1 (snapshot histórico).
- En la Tarea 25 (historial unificado), introducir pruebas **nuevas** "Stage 2-aware" para el
  contrato extendido, y ajustar únicamente las dos aserciones estrictas señaladas, documentando
  el cambio como adaptación planificada (no como corrección de una regresión). La distinción
  entre "preservar valores heredados" y "permitir campos aditivos aprobados" quedará explícita.

**No** se modifica ahora ninguna prueba, requisito, diseño ni decisión. Esto se registra como
consideración de integración futura, no como permiso para implementar el historial unificado.

## Limitaciones heredadas y advertencias conocidas

- La Etapa 1 no heredó suite de pruebas; la Fase A la creó desde cero (por eso este baseline).
- Advertencias en pytest (101, no bloqueantes): `DeprecationWarning: on_event is deprecated`
  (patrón heredado de E1 `@app.on_event("startup")`; migración a `lifespan` planificada en la
  Tarea 12) y alias de anyio en `TestClient`. No afectan a los resultados.

## Métricas del experimento

- **Duración de la sesión:** N/D (no instrumentada). La suite reportó 2,84 s de ejecución.
- **Tokens / créditos / interacciones de herramientas:** N/D (no expuestos al agente). No se
  estiman.

## Archivos creados / modificados en esta tarea

| Acción | Archivo |
|---|---|
| Creado | `_experiment_logs/Kiro/preparacion/E2_KIRO_CHECKPOINT_A_APP_SHA256.csv` (inventario 12 fuentes) |
| Creado | `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_06_CHECKPOINT_A.md` (este registro) |
| Modificado | `.kiro/specs/shift-bank-stage2/tasks.md` (marcada solo la Tarea 6) |

No se modificó código de aplicación, pruebas, fixtures, requisitos, diseño, la Etapa 1 ni
registros experimentales previos.

## Veredicto del checkpoint

**PASS.** 51/51 pruebas verdes; código heredado idéntico al baseline (SHA-256); DB histórica
intacta; aislamiento verificado. La Fase A queda cerrada y el baseline de regresión establecido.
Procede solicitar autorización para la Fase B (Tarea 7), que es la primera que evoluciona el
esquema de BD.
