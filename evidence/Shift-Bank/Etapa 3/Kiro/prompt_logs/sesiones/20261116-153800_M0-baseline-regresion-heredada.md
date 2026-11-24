# Sesión de evidencia — M0: Captura de la regresión heredada verde de partida

- **Etapa:** 3 (Kiro)
- **Tarea:** 1 (auto)(verificación) — Capturar la regresión heredada verde de partida
- **Tipo:** VERIFICACIÓN / EVIDENCIA (no se modificó código de aplicación, pruebas ni SEED-3.md)
- **Fecha/hora de captura:** 2026-11-16 15:38:00 (timestamp del archivo: 20261116-153800)
- **Objetivo:** Ejecutar la suite completa de pruebas del backend heredado y el build de producción
  del frontend sobre el workspace heredado de la Etapa 3, ANTES de cualquier cambio de la Etapa 3,
  preservando stdout crudo y conteos.

---

## 1. Entorno

| Herramienta | Versión |
|-------------|---------|
| Python      | 3.13.2  |
| Node.js     | v24.19.0 |
| npm         | 11.17.0 |
| OS          | Microsoft Windows NT 10.0.26300.0 |

Comando usado:
```
python --version; node --version; npm --version; [System.Environment]::OSVersion.VersionString
```
Salida cruda:
```
Python 3.13.2
v24.19.0
11.17.0
Microsoft Windows NT 10.0.26300.0
```

Aislamiento de DB confirmado: `tests/conftest.py` parchea `app.config.DB_PATH` y `app.db.DB_PATH`
hacia un archivo SQLite temporal único por prueba (vía `tmp_path` + `monkeypatch`), con teardown
que elimina la DB y sus auxiliares (-wal/-shm/-journal). No se toca la DB histórica ni ningún
baseline persistente.

---

## 2. Backend — Suite de pruebas heredada

### 2.1 Directorio de trabajo
```
c:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\Kiro\backend
```

### 2.2 Preparación del entorno (venv + dependencias de desarrollo)
Comando:
```
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```
`requirements-dev.txt` incluye (vía `-r requirements.txt`): fastapi==0.115.5, uvicorn==0.32.1,
pydantic==2.10.3, pytest==8.3.4, httpx==0.28.1.

Resultado de instalación (resumen crudo):
```
Successfully installed annotated-types-0.8.0 anyio-4.16.0 certifi-2026.10.23 click-8.5.1
colorama-0.4.6 fastapi-0.115.5 h11-0.16.0 httpcore-1.0.9 httpx-0.28.1 idna-3.20 iniconfig-2.3.1
packaging-26.3 pluggy-1.7.0 pydantic-2.10.3 pydantic-core-2.27.1 pytest-8.3.4 starlette-0.41.3
typing-extensions-4.16.0 uvicorn-0.32.1
```
Exit code: 0

### 2.3 Ejecución de la suite
Comando:
```
.\.venv\Scripts\python.exe -m pytest -q
```
Salida cruda (stdout):
```
................................................... [ 23%]
................................................... [ 46%]
................................................... [ 69%]
................................................... [ 92%]
................                                    [100%]
==================== warnings summary ====================
tests/test_ach.py::test_crear_y_listar_beneficiario_enmascarado
  C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\Kiro\backend\.venv\Lib\site-packages\starlette\testclient.py:40: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = typing.Callable[[], typing.ContextManager[anyio.abc.BlockingPortal]]
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
220 passed, 1 warning in 14.29s
```

### 2.4 Conteos y verdicto backend
- **Pasadas:** 220
- **Fallidas:** 0
- **Errores:** 0
- **Advertencias:** 1 (DeprecationWarning de starlette/anyio en dependencia de terceros; no es fallo)
- **Exit code:** 0
- **Verdicto backend:** VERDE (100% passing)

Archivos de prueba ejecutados (17): test_ach.py, test_clock.py, test_harness.py, test_limits.py,
test_migration.py, test_migration_suite.py, test_recurring.py, test_recurring_api.py,
test_recurring_execution.py, test_recurring_verification.py, test_regression_accounts.py,
test_regression_api_contracts.py, test_regression_internal_transfers.py, test_regression_mfa.py,
test_scheduler.py, test_schema_stage2.py, test_txn.py.

---

## 3. Frontend — Build de producción

### 3.1 Directorio de trabajo
```
c:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\Kiro\frontend
```

### 3.2 Instalación de dependencias
Comando:
```
npm install
```
Salida cruda (resumen):
```
added 68 packages, and audited 69 packages in 3s
7 packages are looking for funding
2 vulnerabilities (1 moderate, 1 high)
npm warn allow-scripts 1 package has install scripts not yet covered by allowScripts:
npm warn allow-scripts   esbuild@0.21.5 (postinstall: node install.js)
```
Exit code: 0

Nota: los avisos de `npm audit` (2 vulnerabilidades) y `allow-scripts` son advertencias de npm,
no errores de build; no afectan el resultado del `build`.

### 3.3 Build (`tsc && vite build`)
Comando:
```
npm run build
```
Salida cruda (stdout):
```
> shift-bank-frontend@1.0.0 build
> tsc && vite build
vite v5.4.21 building for production...
transforming (1) index.html...
✓ 41 modules transformed.
dist/index.html                   0.40 kB │ gzip:  0.27 kB
dist/assets/index-CX77R-vI.css    4.52 kB │ gzip:  1.38 kB
dist/assets/index-BufvD_Q2.js   169.85 kB │ gzip: 52.58 kB
✓ built in 569ms
```

### 3.4 Verdicto frontend
- **tsc (type-check):** sin errores (el build continuó a vite)
- **vite build:** 41 módulos transformados, `✓ built in 569ms`
- **Exit code:** 0
- **Verdicto frontend:** VERDE (build exitoso)

---

## 4. Veredicto global M0

| Componente | Comando | Exit code | Resultado |
|------------|---------|-----------|-----------|
| Backend (pytest) | `python -m pytest -q` | 0 | 220 passed, 0 failed |
| Frontend (build) | `npm run build` (tsc && vite build) | 0 | build OK |

**VERDICTO: PASS** — La regresión heredada de partida está VERDE antes de cualquier cambio de la
Etapa 3: suite backend 100% passing (exit 0) y build de frontend exitoso (exit 0).

Restricciones respetadas: solo DB temporal/desechable aislada por prueba; no se tocó la DB histórica
de la Etapa 2 ni SEED-3.md; no se modificó código de aplicación ni pruebas.
