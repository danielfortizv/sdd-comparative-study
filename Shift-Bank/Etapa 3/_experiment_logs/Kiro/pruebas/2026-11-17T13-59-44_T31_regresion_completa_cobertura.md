# Tarea 31 — Regresión completa (Pytest + build + Vitest) con cobertura y evidencia (Kiro)

- **Fecha/hora:** 2026-11-17 13:59:44 (-05:00)
- **Workspace:** `Etapa 3/Kiro`
- **Requisitos:** R19.1, R19.2, R14 · **Diseño:** §7, §8 G9 · **AC:** AC-01, AC-14
- **Objetivo:** Regresión completa del backend (Pytest) + build de frontend + Vitest, preservando
  stdout crudo y fallos intermedios, y **generando los informes de cobertura** que la T32
  (PRE-scan de SonarQube) importará:
  - Backend Cobertura XML: `backend/coverage.xml`
  - Frontend LCOV: `frontend/coverage/lcov.info`
- Resultados **no fabricados**: todas las salidas son copias de ejecuciones reales.

---

## Versiones exactas de herramientas

| Herramienta        | Versión                                   | Fuente del comando |
|--------------------|-------------------------------------------|--------------------|
| Python (venv)      | `3.13.2`                                  | `.\.venv\Scripts\python.exe --version` |
| pytest             | `8.3.4`                                   | `python -m pytest --version` |
| coverage.py        | `7.17.3` (con C extension)                | `python -m coverage --version` |
| pytest-cov         | `7.1.0`                                   | `pip show pytest-cov` |
| Node.js            | `v20.17.0`                                | `node --version` |
| npm                | `11.6.3`                                  | `npm --version` |
| Vitest             | `2.1.9` (win32-x64, node-v20.17.0)        | `npx vitest --version` |
| Vite               | `5.4.21` (win32-x64, node-v20.17.0)       | `npx vite --version` |
| @vitest/coverage-v8| `2.1.9` (añadido en esta tarea, solo-dev) | `package.json` + node -e |

---

## Comandos exactos ejecutados

```powershell
# (1) BACKEND regresión con cobertura — desde Etapa 3/Kiro/backend
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pytest --version
.\.venv\Scripts\python.exe -m coverage --version
.\.venv\Scripts\python.exe -m pip show pytest-cov
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=xml:coverage.xml --cov-report=term -q

# (2) FRONTEND build — desde Etapa 3/Kiro/frontend
node --version; npm --version; npx vitest --version; npx vite --version
npm run build

# (3) FRONTEND Vitest con cobertura LCOV — desde Etapa 3/Kiro/frontend
npm install --save-dev "@vitest/coverage-v8@^2.1.8"   # resuelto a 2.1.9
npx vitest run --coverage
npm run build   # re-verificado verde tras el cambio de config
```

Dependencias/herramientas ya presentes (no fue necesario instalarlas): `pytest`, `pytest-cov`,
`coverage` ya estaban en el venv (declaradas en `requirements-dev.txt`).

---

## (1) BACKEND — Pytest con cobertura (REAL)

**Comando:** `.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=xml:coverage.xml --cov-report=term -q`
**Resultado: `372 passed, 2 warnings in 23.23s`. Exit code 0. Cobertura TOTAL = 95%.**

> Nota sobre warnings: aparecen **2** warnings, ninguno es un fallo:
> 1. `DeprecationWarning` preexistente de `starlette/anyio` (`BlockingPortal` alias) en
>    `test_ach.py::test_crear_y_listar_beneficiario_enmascarado` — es la warning de baseline.
> 2. `ResourceWarning` (unclosed sqlite database) en
>    `test_config_failclosed.py::test_lifespan_falla_cerrado_sin_claves`. Es una warning de
>    recurso, no un fallo de aserción; la suite sigue 100% PASS.

Salida cruda (stdout) de pytest:

```
........................................................................ [ 19%]
........................................................................ [ 38%]
........................................................................ [ 58%]
........................................................................ [ 77%]
........................................................................ [ 96%]
............                                                             [100%]
============================== warnings summary ===============================
tests/test_ach.py::test_crear_y_listar_beneficiario_enmascarado
  C:\...\backend\.venv\Lib\site-packages\starlette\testclient.py:40: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = typing.Callable[[], typing.ContextManager[anyio.abc.BlockingPortal]]
tests/test_config_failclosed.py::test_lifespan_falla_cerrado_sin_claves
  C:\...\backend\.venv\Lib\site-packages\pydantic\_internal\_core_utils.py:194: ResourceWarning: unclosed database in <sqlite3.Connection object at 0x000002131E880E50>
    def _walk(self, schema: core_schema.CoreSchema, f: Walk) -> core_schema.CoreSchema:
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=============================== tests coverage ================================
_______________ coverage: platform win32, python 3.13.2-final-0 _______________
Name                           Stmts   Miss  Cover
--------------------------------------------------
app\__init__.py                    0      0   100%
app\ach_repository.py             62      1    98%
app\ach_service.py               140     13    91%
app\audit.py                     101      6    94%
app\beneficiaries.py              27      2    93%
app\clock.py                      34      0   100%
app\config.py                     66      4    94%
app\crypto.py                     84      6    93%
app\db.py                         59      0   100%
app\limit_service.py              66      4    94%
app\main.py                       36      0   100%
app\money.py                      31      4    87%
app\recurring_service.py         216      8    96%
app\repository.py                120     10    92%
app\routers\__init__.py            0      0   100%
app\routers\accounts.py           15      0   100%
app\routers\ach.py                44      0   100%
app\routers\audit.py              39      3    92%
app\routers\beneficiaries.py      59      2    97%
app\routers\limits.py             35      0   100%
app\routers\recurring.py          73      0   100%
app\routers\transfers.py          53      0   100%
app\scheduler.py                  77      6    92%
app\schemas.py                    40      0   100%
app\seed.py                       38      1    97%
app\service.py                   115      9    92%
app\txn.py                        16      0   100%
--------------------------------------------------
TOTAL                           1646     79    95%
Coverage XML written to file coverage.xml
372 passed, 2 warnings in 23.23s
```

**Cobertura XML escrita:** `coverage.xml` — cabecera confirmada:
`<coverage version="7.17.3" ... lines-valid="1646" lines-covered="1567" line-rate="0.952" ...>`
(line-rate 0.952 = **95%**).

---

## (2) FRONTEND — build de producción (REAL)

**Comando:** `npm run build`  (`tsc && vite build`)
**Resultado: exit 0 (tsc sin errores + vite build OK).**

```
> shift-bank-frontend@1.0.0 build
> tsc && vite build
vite v5.4.21 building for production...
transforming...
✓ 41 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.40 kB │ gzip:  0.27 kB
dist/assets/index-CX77R-vI.css    4.52 kB │ gzip:  1.38 kB
dist/assets/index-uDwVUt2C.js   169.82 kB │ gzip: 52.56 kB
✓ built in 734ms
```

Re-verificado **verde** tras el cambio de config de Vitest (ver sección 3): segundo `npm run build`
exit 0, `built in 791ms`, mismos artefactos. El bloque `test.coverage` de `vite.config.ts` no
afecta al build de producción (Vite ignora `test` fuera de Vitest).

---

## (3) FRONTEND — Vitest con cobertura LCOV (REAL)

### Dependencia de dev añadida

| Paquete                | Rango package.json | Versión resuelta | Tipo |
|------------------------|--------------------|------------------|------|
| `@vitest/coverage-v8`  | `^2.1.9`           | `2.1.9`          | **devDependency** (solo-dev) |

- `npm install --save-dev "@vitest/coverage-v8@^2.1.8"` → `added 59 packages` (exit 0).
  (La única advertencia fue una deprecación transitiva de `glob` enrutada a stderr por npm; no es
  un fallo. El audit reporta vulnerabilidades en el árbol de **devDependencies** de pruebas; no
  afecta al runtime ni a la app.)
- **Sin** nuevas dependencias de `dependencies` (runtime). `react`/`react-dom` intactas.

### Cambio de configuración (mínimo) en `vite.config.ts`

Se añadió un bloque `coverage` dentro del `test` ya existente:
```ts
coverage: {
  provider: "v8",
  reporter: ["text", "lcov"],
  reportsDirectory: "coverage",
},
```
No se alteró el código de la aplicación ni el script `build`.

### `npx vitest run --coverage` → PASS

**Resultado: `3 passed (3)` — Test Files 1 passed (1). Exit code 0. LCOV generado.**

```
 RUN  v2.1.9 .../Etapa 3/Kiro/frontend
      Coverage enabled with v8
 ✓ src/api/client.test.ts (3 tests) 7ms
 Test Files  1 passed (1)
      Tests  3 passed (3)
   Start at  13:59:25
   Duration  634ms (transform 53ms, setup 0ms, collect 48ms, tests 7ms, environment 0ms, prepare 163ms)
 % Coverage report from v8
-------------------|---------|----------|---------|---------|-------------------
File               | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s 
-------------------|---------|----------|---------|---------|-------------------
All files          |    2.78 |    31.81 |   19.35 |    2.78 |                   
 src               |       0 |        0 |       0 |       0 |                   
  App.tsx          |       0 |        0 |       0 |       0 | 1-205             
  main.tsx         |       0 |        0 |       0 |       0 | 1-11              
  types.ts         |       0 |        0 |       0 |       0 | 1-228             
 src/api           |      50 |       70 |   31.57 |      50 |                   
  client.ts        |      50 |       70 |   31.57 |      50 | ...59-162,169-170 
 src/components    |       0 |        0 |       0 |       0 |                   
  ...untsPanel.tsx |       0 |        0 |       0 |       0 | 1-33              
  ...nsferForm.tsx |       0 |        0 |       0 |       0 | 1-278             
  ...riesPanel.tsx |       0 |        0 |       0 |       0 | 1-172             
  HistoryList.tsx  |       0 |        0 |       0 |       0 | 1-84              
  LimitsPanel.tsx  |       0 |        0 |       0 |       0 | 1-136             
  MfaDialog.tsx    |       0 |        0 |       0 |       0 | 1-125             
  ...ringPanel.tsx |       0 |        0 |       0 |       0 | 1-464             
  TransferForm.tsx |       0 |        0 |       0 |       0 | 1-112             
  ...Validation.ts |       0 |        0 |       0 |       0 | 1-19              
-------------------|---------|----------|---------|---------|-------------------
```

**Cobertura frontend global (v8): 2.78% líneas** — esperado: las 3 pruebas de humo (T30) solo
ejercitan `src/api/client.ts` (50% líneas en ese archivo). El resto de la app (componentes React,
`App.tsx`, `types.ts`) no está cubierta por las pruebas de humo. Esto es correcto y documentado;
no se fabrica cobertura. **LCOV generado:** `coverage/lcov.info` (confirmado: cabecera `TN:` /
`SF:src\App.tsx`).

---

## Artefactos de cobertura preservados para T32 (SonarQube PRE-scan)

> NO BORRAR. Son entradas de importación del escáner (artefactos git-ignored, es lo esperado).
> Rutas EXACTAS que espera la plantilla del escáner T4
> (`sonar.python.coverage.reportPaths=backend/coverage.xml`,
> `sonar.javascript.lcov.reportPaths=frontend/coverage/lcov.info`):

| Artefacto            | Ruta relativa a `Etapa 3/Kiro/` | Ruta absoluta |
|----------------------|---------------------------------|---------------|
| Backend Cobertura XML| `backend/coverage.xml`          | `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\Kiro\backend\coverage.xml` |
| Frontend LCOV        | `frontend/coverage/lcov.info`   | `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\Kiro\frontend\coverage\lcov.info` |

---

## Veredicto de verificación (T31)

| Criterio                                   | Resultado |
|--------------------------------------------|-----------|
| Backend 100% PASS (esperado 372)           | ✅ **372 passed**, exit 0 (2 warnings, no fallos) |
| Backend coverage.xml generado              | ✅ `backend/coverage.xml`, line-rate 0.952 (**95%**) |
| Build frontend exit 0                      | ✅ `tsc && vite build` exit 0 (antes y después del cambio de config) |
| Vitest PASS (esperado 3)                   | ✅ **3 passed**, exit 0 |
| Frontend LCOV generado                     | ✅ `frontend/coverage/lcov.info` (cobertura global 2.78%, documentada) |
| Evidencia cruda preservada                 | ✅ este archivo (no sobrescribe evidencia previa) |

## Notas de integridad experimental

- Resultados **no fabricados**: todas las salidas son copias de ejecuciones reales (exit 0 en todas).
- **No** se modificó código fuente de la app para "arreglar" nada. Único cambio no-prueba: bloque
  `coverage` mínimo en `vite.config.ts` (solo afecta a Vitest) + `@vitest/coverage-v8` como
  devDependency.
- Backend sin cambios; baseline de 372 pruebas intacta.
- **D-E3-01..04 preservados** (no se tocaron decisiones ni artefactos heredados).
- **Fallos intermedios:** ninguno. Todas las ejecuciones fueron exit 0 en el primer intento.
