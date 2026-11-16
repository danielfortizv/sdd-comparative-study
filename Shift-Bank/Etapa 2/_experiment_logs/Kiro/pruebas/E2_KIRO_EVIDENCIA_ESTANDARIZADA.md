# E2 · Kiro · Evidencia estandarizada (código, pruebas, análisis estático) — Tarea 46

- **Fecha de recolección:** 2026-11-16
- **Tarea:** 46 — Recolectar evidencia estandarizada (código, pruebas, análisis estático)
- **Fase:** G — Verificación final y evidencia experimental
- **Contrato:** §7
- **Naturaleza:** recolección de evidencia. **No** crea ni modifica código de aplicación,
  pruebas, requisitos, diseño ni registros históricos. Todos los números se obtuvieron ejecutando
  comandos **frescos** en esta tarea. **No se fabrican resultados ni métricas.**

---

## 1. Entorno de medición (real, re-verificado en esta tarea)

- **SO:** Windows; shell PowerShell.
- **Backend:** Python **3.13.2** (`.venv\Scripts\python.exe`), pytest **8.3.4**.
- **Frontend:** Node **v24.19.0**, TypeScript **5.9.3** (type-check).
- Conteos de líneas con `Get-Content | Measure-Object -Line`; exclusiones: `__pycache__`,
  `node_modules`, `dist`, `.venv`.

---

## 2. Evidencia de código (recuento real de archivos y líneas)

### 2.1 Resumen

| Ámbito | Archivos | Líneas |
|---|---:|---:|
| Backend — `backend/app/**.py` (producción) | 24 | 2.896 |
| Backend — `backend/tests/**.py` (pruebas) | 18 | 3.270 |
| Frontend — `frontend/src/**` (producción) | 14 | 2.180 |

> Frontend por extensión: `.tsx` 10 archivos / 1.493 líneas · `.ts` 3 archivos / 353 líneas ·
> `.css` 1 archivo / 334 líneas.

### 2.2 Backend `app/` — detalle por archivo (líneas)

| Líneas | Archivo |
|---:|---|
| 555 | `app/recurring_service.py` |
| 416 | `app/repository.py` |
| 199 | `app/ach_service.py` |
| 180 | `app/service.py` |
| 176 | `app/db.py` |
| 157 | `app/routers/recurring.py` |
| 144 | `app/scheduler.py` |
| 138 | `app/ach_repository.py` |
| 129 | `app/routers/transfers.py` |
| 116 | `app/seed.py` |
| 113 | `app/limit_service.py` |
| 71 | `app/clock.py` |
| 68 | `app/routers/ach.py` |
| 68 | `app/routers/beneficiaries.py` |
| 59 | `app/routers/limits.py` |
| 54 | `app/main.py` |
| 54 | `app/txn.py` |
| 51 | `app/money.py` |
| 44 | `app/schemas.py` |
| 43 | `app/beneficiaries.py` |
| 39 | `app/config.py` |
| 22 | `app/routers/accounts.py` |
| 0 | `app/__init__.py` |
| 0 | `app/routers/__init__.py` |
| **2.896** | **Total (24 archivos)** |

### 2.3 Frontend `src/` — detalle por archivo (líneas)

| Líneas | Archivo |
|---:|---|
| 434 | `src/components/RecurringPanel.tsx` |
| 334 | `src/styles/global.css` |
| 256 | `src/components/AchTransferForm.tsx` |
| 191 | `src/types.ts` |
| 185 | `src/App.tsx` |
| 160 | `src/components/BeneficiariesPanel.tsx` |
| 145 | `src/api/client.ts` |
| 124 | `src/components/LimitsPanel.tsx` |
| 113 | `src/components/MfaDialog.tsx` |
| 105 | `src/components/TransferForm.tsx` |
| 78 | `src/components/HistoryList.tsx` |
| 29 | `src/components/AccountsPanel.tsx` |
| 17 | `src/components/beneficiaryValidation.ts` |
| 9 | `src/main.tsx` |
| **2.180** | **Total (14 archivos)** |

---

## 3. Evidencia de pruebas (recuento real + resultado de la suite)

### 3.1 Suite backend completa (re-ejecución fresca en esta tarea)

```
.\.venv\Scripts\python.exe -m pytest -q
```

| Métrica | Valor real |
|---|---|
| Resultado | **220 passed, 0 failed, 0 skipped, 1 warning** |
| Duración (reportada por pytest) | 14,33 s |
| Código de salida | **0** |
| Colección (`--collect-only -q`) | **220 tests collected** |

Advertencia única: `DeprecationWarning` de `anyio.abc.BlockingPortal` emitido por
`starlette.testclient`; depende de la librería, no del código de la aplicación.

### 3.2 Métricas agregadas de pruebas (conteo estático fresco)

| Métrica | Valor real |
|---|---:|
| Archivos de prueba | 18 (`tests/*.py`) |
| Casos de prueba recolectados (pytest) | 220 |
| Definiciones `def test_…` (grep) | 210 |
| Sentencias `assert` (grep) | 577 |
| Líneas totales de prueba | 3.270 |

> Nota: los 220 casos recolectados superan las 210 definiciones `def test_…` porque hay pruebas
> **parametrizadas** (una definición genera varios casos). Ambos números son reales y se citan
> tal cual los reporta la herramienta.

### 3.3 Inventario por archivo (recuento `pytest --collect-only`)

| Casos | Archivo | Dominio |
|---:|---|---|
| 4 | `tests/test_harness.py` | Arnés / aislamiento de DB temporal |
| 6 | `tests/test_migration.py` | Fase B — migración idempotente/transaccional |
| 7 | `tests/test_migration_suite.py` | Fase B — migración sobre copia real + E2E |
| 8 | `tests/test_regression_accounts.py` | Fase A — cuentas y saldos iniciales |
| 8 | `tests/test_scheduler.py` | Fase E — scheduler de fondo (único worker) |
| 9 | `tests/test_txn.py` | Fase B — transacción financiera reutilizable |
| 10 | `tests/test_clock.py` | Fase B — reloj inyectable |
| 11 | `tests/test_limits.py` | Fase C — límites dinámicos y concurrencia |
| 12 | `tests/test_regression_internal_transfers.py` | Fase A — internas heredadas |
| 12 | `tests/test_schema_stage2.py` | Fase B — esquema de tablas nuevas |
| 13 | `tests/test_regression_api_contracts.py` | Fase A — contratos de API e historial |
| 14 | `tests/test_recurring_api.py` | Fase E — endpoints recurrentes |
| 14 | `tests/test_regression_mfa.py` | Fase A — MFA heredada |
| 16 | `tests/test_ach.py` | Fase D — beneficiarios + ACH |
| 18 | `tests/test_recurring_execution.py` | Fase E — ejecución durable y atómica |
| 21 | `tests/test_recurring_verification.py` | Fase E — verificación A15–A19/D06/una-vez |
| 37 | `tests/test_recurring.py` | Fase E — creación/MFA/ciclo de vida |
| **220** | **Total (17 archivos con casos + conftest)** | |

> `tests/conftest.py` no aporta casos (fixtures de aislamiento). Total de archivos `.py` en
> `tests/` = 18; archivos que aportan casos recolectados = 17.

---

## 4. Evidencia de análisis estático

El estado real del análisis estático estandarizado se documenta en
`../sonarqube/README.md`. Resumen:

| Herramienta | Estado en E2·Kiro | Resultado |
|---|---|---|
| SonarQube (escaneo + `sonar-project.properties`) | No ejecutado / no configurado en el proyecto | — (no se fabrica) |
| Linter Python (ruff/flake8/pylint/mypy/bandit/…) | No instalado ni configurado | — |
| ESLint (frontend) | No configurado | — |
| **TypeScript `tsc --noEmit`** | Presente y **ejecutado fresco** | **0 errores, exit 0** (tsc 5.9.3) |

Antecedente (otra etapa, no reutilizado): `Etapa 1/_experiment_logs/Kiro/sonarqube_scan_001.txt`
(SonarQube de la **Etapa 1**, `ANALYSIS SUCCESSFUL`).

---

## 5. Preservación / no manipulación

- DB histórica `Etapa 1/Kiro/backend/shift_bank.db`: SHA-256
  `407B0E132E76900FBF59412C31A2D8047A666F2BE1856BE1FF6B88531C89B4A8`, 36.864 bytes — recalculado
  en esta tarea, **idéntico** al invariante registrado en las sesiones previas.
- Esta tarea solo ejecutó comandos de lectura/análisis y escribió documentos de evidencia. No se
  modificó código de aplicación, pruebas, requisitos, diseño, la Etapa 1 ni registros previos.
- Los números de pruebas (220/220) y los artefactos del build (Tarea 42) coinciden con los ya
  consolidados en `E2_KIRO_RESULTADOS_PRUEBAS.md` (Tarea 45): la evidencia es estable.

## 6. Archivos creados en esta tarea

| Acción | Archivo |
|---|---|
| Creado | `_experiment_logs/Kiro/sonarqube/README.md` |
| Creado | `_experiment_logs/Kiro/pruebas/E2_KIRO_EVIDENCIA_ESTANDARIZADA.md` (este archivo) |
| Creado | `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_31_TAREA_46.md` |
| Modificado | `.kiro/specs/shift-bank-stage2/tasks.md` (marca de la Tarea 46) |
