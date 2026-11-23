# E2 · Kiro · Sesión de implementación 32 — Tareas 47–50 (pasada correctiva SonarQube)

- **Fecha:** 2026-11-16
- **Tareas:** 47, 48, 49 (correctivas) y 50 (verificación) — Fase H, pasada correctiva de SonarQube
- **Fase:** H — Pasada correctiva de SonarQube (PRE scan manual del investigador)
- **Objetivo de esta sesión (Tarea 50):** verificar que las correcciones de las Tareas 47–49 no
  introdujeron regresiones, ejecutando la suite backend completa + suites enfocadas + build de
  producción del frontend, y registrar evidencia real de los issues corregidos y los
  conscientemente diferidos.
- **Alcance autorizado:** solo verificación/evidencia de la Tarea 50 (las Tareas 47–49 ya fueron
  aplicadas). Tarea de **verificación pura**; **sin modificar código de producción**, pruebas,
  requisitos, diseño, la evidencia PRE de SonarQube ni la Etapa 1. **No** se re-ejecuta SonarQube.
- **Estado final:** verificación PASS — 220/220 backend, build exit 0, DB histórica E1 intacta.
  La Tarea 50 queda lista para su marca por el orquestador; **A21 (Tarea 43) NO se marca**.
- **Contrato:** A20, §7 · **SonarQube:** pasada correctiva (S7497, S1192, S3358, S7721, S6759).

## Naturaleza de la tarea

Tarea puramente de **verificación**. No crea ni modifica código de aplicación ni pruebas. Ejecuta
comandos de **lectura/análisis** (`pytest`, `npm run build`, `Get-FileHash`) y consigna los
resultados. **No se fabrican resultados ni métricas.** El escaneo POST de SonarQube es
responsabilidad del investigador y **no** se ejecutó aquí.

## Entorno de ejecución

- Backend ejecutado desde `Etapa 2/Kiro/backend` con el intérprete del entorno virtual
  (`.venv\Scripts\python.exe`): **Python 3.13.2**, **pytest 8.3.4**.
- Frontend ejecutado desde `Etapa 2/Kiro/frontend`: **Node v24.19.0**, **npm 11.17.0**,
  **vite v5.4.21**, TypeScript ^5.6.3.
- **SO:** Windows; shell PowerShell.
- DB histórica de referencia: `Etapa 1/Kiro/backend/shift_bank.db` (36.864 bytes).

## Entrada — baseline PRE de SonarQube (citada, NO modificada)

Fuente: `_experiment_logs/Kiro/sonarqube/E2_KIRO_SONAR_PRE_*.{json,log}` (escaneo manual del
investigador). Valores reales leídos:

| Métrica | Valor PRE |
|---|---|
| Quality Gate | **OK** (`caycStatus: compliant`, sin condiciones fallidas) |
| Bugs | **1** |
| Code smells | **58** |
| Vulnerabilidades | **0** |
| NCLOC | **4.236** |
| Duplicación (`duplicated_lines_density`) | **0.0 %** |
| Deuda técnica (`sqale_index`) | **318 min** |
| Cobertura | **0.0 %** (sin datos de cobertura importados al escáner) |
| Complejidad cognitiva | 352 |

Estos ficheros PRE **no** fueron modificados en esta sesión.

## Correcciones aplicadas en la pasada (Tareas 47–49) — verificadas presentes

**13 issues abordados.** Archivos tocados y verificación de presencia:

| Tarea | Issue(s) SonarQube | Sev. | Archivo(s) | Estado |
|---|---|---|---|---|
| 47 | `python:S7497` (BUG) ×1 | HIGH | `backend/app/scheduler.py` (`Scheduler.stop()`) | Verificado: `except asyncio.CancelledError` ahora re-lanza cuando `task` no está cancelada (cancelación del propio `stop()`), y solo absorbe la cancelación de la tarea worker. Apagado limpio (Req. 10.2) preservado. |
| 48 | `python:S1192` (CRITICAL) ×1 | HIGH | `backend/app/repository.py` | Verificado: literal `"SELECT * FROM recurring_schedule WHERE id = ?"` (×3) reemplazado por la constante de módulo `_SELECT_SCHEDULE_BY_ID`. SQL emitido sin cambios. |
| 49 | `typescript:S3358` (MAJOR) ×2 | — | `frontend/src/components/HistoryList.tsx`, `RecurringPanel.tsx` | Ternario anidado extraído. |
| 49 | `typescript:S7721` (MAJOR) ×1 | — | `frontend/src/components/AchTransferForm.tsx` | `statusMessage` movido al scope exterior. |
| 49 | `typescript:S6759` (MINOR) ×8 | — | `AccountsPanel, AchTransferForm, BeneficiariesPanel, HistoryList, LimitsPanel, MfaDialog, RecurringPanel, TransferForm` (`.tsx`) | Props marcadas `Readonly<Props>` (verificadas las 8). |

Total: 1 (S7497) + 1 (S1192) + 2 (S3358) + 1 (S7721) + 8 (S6759) = **13 issues**.

## Issues conscientemente DIFERIDOS (con justificación)

No se corrigen en esta pasada para no arriesgar comportamiento aprobado, por bajo valor o por alto
churn cosmético:

| Issue | Cantidad | Ubicación / tipo | Justificación del diferimiento |
|---|---|---|---|
| `typescript:S6772` "ambiguous spacing" | ×37 | Espaciado JSX cosmético | Sin impacto conductual; alto churn de diff; no altera la UI renderizada. |
| `python:S107` (demasiados parámetros) | ×1 | `create_schedule` (15 parámetros) | La firma refleja la amplitud del esquema aprobado (D02/D06); refactorizar arriesga el contrato repositorio/servicio. |
| `python:S8410` | ×5 | Convención FastAPI `Annotated`/`response_model` | Convención idiomática; bajo valor; parte en código heredado de la Etapa 1. |
| `python:S8409` | ×1 | Convención FastAPI (`accounts.py`, heredado E1) | Heredado de la Etapa 1; bajo valor; cambiarlo toca contrato E1. |
| `typescript:S8786` | ×1 | Regex en `AccountsPanel.tsx` (heredado E1) | Heredado E1; cambiar el regex arriesga alterar el formato COP preservado. |
| `typescript:S6819` | ×1 | `MfaDialog` `role="dialog"` → `<dialog>` nativo | Accesibilidad, pero migrar a `<dialog>` cambia semántica de foco/backdrop/`showModal` y arriesga la UX de MFA aprobada; diferido para evitar cambio de comportamiento. |

## Evidencia 1 — Suites enfocadas (pytest)

Comando (desde `Etapa 2/Kiro/backend`):

```
.\.venv\Scripts\python.exe -m pytest tests/test_scheduler.py tests/test_recurring.py \
    tests/test_recurring_execution.py tests/test_recurring_api.py -q
```

Resultado real: **77 passed, 0 failed, 0 skipped, 1 warning** — exit **0** — 5,76 s.
Cubre directamente el código tocado por las Tareas 47 (`scheduler.py`) y 48 (`repository.py`,
rutas de recurrentes). Advertencia no bloqueante: 1 `DeprecationWarning` de
`anyio.abc.BlockingPortal` (alias usado por `starlette.testclient`), de la dependencia, no del
código de la aplicación.

## Evidencia 2 — Suite backend completa (pytest)

Comando: `.\.venv\Scripts\python.exe -m pytest -q`

Resultado real: **220 passed, 0 failed, 0 skipped, 1 warning** — exit **0** — 14,93 s.
Idéntico al baseline de 220 pruebas registrado en las Tareas 40–46. **Cero regresiones** tras las
correcciones 47–49.

## Evidencia 3 — Build de producción del frontend

Comando (desde `Etapa 2/Kiro/frontend`): `npm run build` (`tsc && vite build`).

Resultado real: exit **0**. `tsc` sin errores (las props `Readonly<>` y las extracciones de
ternario/variable compilan limpias). **41 módulos transformados**, build en 648 ms. Artefactos en
`frontend/dist/`:

| Artefacto | Tamaño | gzip |
|---|---|---|
| `dist/index.html` | 0,40 kB | 0,26 kB |
| `dist/assets/index-CX77R-vI.css` | 4,52 kB | 1,38 kB |
| `dist/assets/index-sddi8Nqi.js` | 169,86 kB | 52,59 kB |

## Evidencia 4 — No manipulación de la DB histórica de la Etapa 1

| Momento | SHA-256 de `Etapa 1/Kiro/backend/shift_bank.db` | Tamaño |
|---|---|---|
| Recalculado en esta sesión | `407B0E132E76900FBF59412C31A2D8047A666F2BE1856BE1FF6B88531C89B4A8` | 36.864 bytes |

Hash **idéntico** al invariante registrado en las sesiones 06, 08, 10, 27–31 y en las Tareas
44–46. La DB histórica de la Etapa 1 **nunca fue tocada**.

## Límites y pendientes

- **Escaneo POST de SonarQube:** responsabilidad del investigador; **NO** ejecutado en esta sesión
  (no hay `sonar-project.properties` en `Etapa 2/Kiro`). No se fabrican métricas POST.
- **A21 (Tarea 43):** sigue pendiente de evidencia manual real de navegador; **NO** se marca
  completa. Estado previo `[-]` preservado.
- Limitación F13 (FK no declarable vía ALTER en `transfer`) y el campo aditivo `type` siguen según
  lo documentado; no se tocan aquí.

## Errores y correcciones

- Ninguno en esta sesión de verificación. Las 77 pruebas enfocadas, las 220 de la suite completa y
  el build de producción pasaron en la primera ejecución. No se corrigió comportamiento ni se tocó
  ninguna prueba o código de aplicación.

## No modificación de código de producción

Esta sesión solo ejecutó comandos de lectura/análisis (`pytest`, `npm run build`, `Get-FileHash`)
y escribió documentos de evidencia. No se editó `app/`, ni las pruebas, ni el frontend, ni la
Etapa 1, ni la evidencia PRE de SonarQube, ni registros previos. Sin dependencias nuevas.

## Métricas

- **Pruebas enfocadas:** 77/77 PASS (exit 0, 5,76 s).
- **Suite completa:** 220/220 PASS (exit 0, 14,93 s) — sin regresión frente al baseline de 220.
- **Build frontend:** exit 0; 41 módulos; `js` 169,86 kB, `css` 4,52 kB, `html` 0,40 kB.
- **Issues corregidos en la pasada:** 13 (S7497 ×1, S1192 ×1, S3358 ×2, S7721 ×1, S6759 ×8).
- **Issues diferidos:** S6772 ×37, S107 ×1, S8410 ×5, S8409 ×1, S8786 ×1, S6819 ×1.
- **DB histórica E1:** SHA-256 `407B0E13…` sin cambios (36.864 bytes).
- **Duración:** N/D (no instrumentada). pytest reportó 5,76 s (enfocadas) y 14,93 s (completa);
  build 648 ms.
- **Tokens / créditos / interacciones de herramientas:** N/D (no expuestos). No se estiman.

## Archivos creados / modificados en esta tarea

| Acción | Archivo |
|---|---|
| Creado | `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_32_TAREA_47_50.md` (este registro) |
| Creado | `_experiment_logs/Kiro/pruebas/E2_KIRO_RESULTADOS_PASADA_CORRECTIVA_SONAR.md` |

## Alcance / restricciones respetadas

- Solo se verificó la Tarea 50. Las Tareas 1–49 se preservan según su estado; la Tarea 43 (A21
  manual) queda en `[-]` sin marcar.
- No se modificó código de aplicación, pruebas, requisitos, diseño, la Etapa 1, la evidencia PRE
  de SonarQube ni registros previos. No se re-ejecutó SonarQube. No se fabricaron resultados ni
  métricas.
