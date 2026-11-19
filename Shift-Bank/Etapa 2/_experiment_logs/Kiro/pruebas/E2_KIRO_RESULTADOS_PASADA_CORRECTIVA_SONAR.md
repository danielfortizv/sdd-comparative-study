# E2 · Kiro · Resultados de la pasada correctiva de SonarQube (Tareas 47–50)

- **Fecha:** 2026-11-16
- **Fase:** H — Pasada correctiva de SonarQube
- **Tareas:** 47–49 (correctivas) · 50 (verificación)
- **Contrato:** A20, §7 · **SonarQube:** S7497, S1192, S3358, S7721, S6759
- **Naturaleza:** registro de resultados **reales** de verificación tras las correcciones. No
  modifica código de producción, pruebas ni la evidencia PRE de SonarQube. No se re-ejecuta
  SonarQube (POST scan = responsabilidad del investigador). **No se fabrican resultados.**

> Fuente de detalle: `../sesiones/E2_KIRO_SESION_32_TAREA_47_50.md`. Entrada PRE citada desde
> `../sonarqube/E2_KIRO_SONAR_PRE_*.{json,log}` (no modificada).

---

## 1. Entorno

- Backend: `Etapa 2/Kiro/backend`, `.venv\Scripts\python.exe` — Python **3.13.2**, pytest **8.3.4**.
- Frontend: `Etapa 2/Kiro/frontend` — Node **v24.19.0**, npm **11.17.0**, vite **v5.4.21**.
- SO: Windows / PowerShell.

## 2. Baseline PRE de SonarQube (entrada — NO modificada)

Quality Gate **OK** · **1** bug · **58** code smells · **0** vulnerabilidades · **4.236** NCLOC ·
**0,0 %** duplicación · **318 min** de deuda (`sqale_index`) · **0,0 %** coverage (sin datos de
cobertura importados) · complejidad cognitiva 352.

## 3. Issues corregidos en la pasada (13)

| Issue | Sev. | ×N | Archivo(s) |
|---|---|---:|---|
| `python:S7497` (BUG, RELIABILITY/HIGH) | HIGH | 1 | `backend/app/scheduler.py` — `Scheduler.stop()` re-lanza `CancelledError` del propio `stop()`; absorbe solo la de la tarea worker. |
| `python:S1192` (CRITICAL, MAINTAINABILITY/HIGH) | HIGH | 1 | `backend/app/repository.py` — constante `_SELECT_SCHEDULE_BY_ID` sustituye el literal ×3; SQL sin cambios. |
| `typescript:S3358` (MAJOR) | — | 2 | `HistoryList.tsx`, `RecurringPanel.tsx` — ternario anidado extraído. |
| `typescript:S7721` (MAJOR) | — | 1 | `AchTransferForm.tsx` — `statusMessage` al scope exterior. |
| `typescript:S6759` (MINOR) | — | 8 | `AccountsPanel, AchTransferForm, BeneficiariesPanel, HistoryList, LimitsPanel, MfaDialog, RecurringPanel, TransferForm` — props `Readonly<Props>`. |

Total = 1 + 1 + 2 + 1 + 8 = **13**.

## 4. Issues conscientemente diferidos

| Issue | ×N | Razón |
|---|---:|---|
| `typescript:S6772` ("ambiguous spacing") | 37 | Espaciado JSX cosmético; sin impacto conductual; alto churn. |
| `python:S107` (`create_schedule`, 15 params) | 1 | La firma refleja la amplitud del esquema aprobado; refactor arriesga el contrato repositorio/servicio. |
| `python:S8410` | 5 | Convención FastAPI `Annotated`/`response_model`; bajo valor. |
| `python:S8409` | 1 | `accounts.py` heredado de la Etapa 1; bajo valor. |
| `typescript:S8786` (regex) | 1 | `AccountsPanel.tsx` heredado E1; cambiar arriesga el formato COP preservado. |
| `typescript:S6819` (`role="dialog"` → `<dialog>`) | 1 | `MfaDialog`: migrar a `<dialog>` cambia foco/backdrop/`showModal` y arriesga la UX de MFA aprobada. |

## 5. Resultados reales de verificación (Tarea 50)

| Comando | Resultado | Exit |
|---|---|---|
| `pytest tests/test_scheduler.py tests/test_recurring.py tests/test_recurring_execution.py tests/test_recurring_api.py -q` | **77 passed, 0 failed, 0 skipped, 1 warning** (5,76 s) | 0 |
| `pytest -q` (suite completa) | **220 passed, 0 failed, 0 skipped, 1 warning** (14,93 s) | 0 |
| `npm run build` (`tsc && vite build`) | **exit 0**; `tsc` sin errores; 41 módulos (648 ms) | 0 |

Artefactos del build: `dist/index.html` 0,40 kB · `dist/assets/index-CX77R-vI.css` 4,52 kB ·
`dist/assets/index-sddi8Nqi.js` 169,86 kB. Baseline de 220 pruebas preservado → **cero
regresiones**. Advertencia única = `DeprecationWarning` de `anyio.abc.BlockingPortal` (dependencia
`starlette.testclient`), no bloqueante.

## 6. No manipulación de la DB histórica de la Etapa 1

| Momento | SHA-256 de `Etapa 1/Kiro/backend/shift_bank.db` | Tamaño |
|---|---|---|
| Recalculado en esta sesión | `407B0E132E76900FBF59412C31A2D8047A666F2BE1856BE1FF6B88531C89B4A8` | 36.864 bytes |

Idéntico al invariante de sesiones previas. DB histórica **intacta**.

## 7. Pendientes y responsabilidades

- **POST scan de SonarQube:** NO ejecutado; responsabilidad del investigador. No se fabrican
  métricas POST.
- **A21 (Tarea 43):** pendiente de evidencia manual real de navegador; NO marcada completa.
- **Métricas de esfuerzo:** duración solo según lo reportado por las herramientas (pytest 5,76 s /
  14,93 s; build 648 ms). Tokens/créditos/interacciones: **N/D** (no expuestos), consistente con
  registros previos.

## 8. Restricciones respetadas

Verificación + evidencia pura. Sin modificar código de producción, pruebas, la evidencia PRE de
SonarQube ni la Etapa 1. Sin re-ejecutar SonarQube. A21 no marcada. Sin fabricar resultados.
