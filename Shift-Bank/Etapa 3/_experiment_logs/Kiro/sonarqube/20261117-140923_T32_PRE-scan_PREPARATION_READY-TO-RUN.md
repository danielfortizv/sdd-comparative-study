# T32 — Escaneo SonarQube PRE-remediación (Etapa 3, workspace Kiro)

## REGISTRO DE PREPARACIÓN / READY-TO-RUN

- **Fecha/hora (local):** 2026-11-17 14:09:23
- **Tarea:** T32 — Escaneo SonarQube PRE-remediación de la Etapa 3
- **Requisitos:** R19.3, R19.4 · **Diseño:** §9, §8 G9 · **AC:** AC-15, AC-16
- **Estado de la tarea:** **BLOQUEADA / DETENIDA — pendiente de ejecución por el investigador.**
  El escaneo autenticado NO se ejecutó. **No se fabricó ningún resultado**
  (ni issues, ni Quality Gate, ni analysis ID, ni task id). Esta tarea queda
  en pausa hasta que el investigador ejecute el escaneo (gate T33).

> **Por qué está detenida (no es PASS):** el escaneo autenticado requiere un
> `SONAR_TOKEN` que sólo posee el investigador; el protocolo experimental
> designa los escaneos de Sonar como ejecutados-por-el-investigador. Un escáner
> no ejecutable de forma desatendida (sin token) **NO es un PASS**. No se
> adivinaron ni se forzaron credenciales.

---

## 1. Verificación REAL de precondiciones no-autenticadas

Todas verificadas en vivo durante la preparación (no fabricadas):

### 1.1 Servidor SonarQube accesible — OK
`GET http://localhost:9000/api/system/status` →
```json
{"id":"147B411E-AaDu3RAtjbxfUIRaFUSu","version":"26.9.0.129388","status":"UP"}
```
- status: **UP** · versión **26.9.0.129388**.

### 1.2 Cobertura backend `backend/coverage.xml` — OK (Cobertura XML válido)
- Ruta: `Etapa 3/Kiro/backend/coverage.xml` · existe · tamaño 65297 bytes · modificado 2026-11-17 13:58:44.
- Cabecera Cobertura (real):
```xml
<coverage version="7.17.3" timestamp="1794941924193" lines-valid="1646"
          lines-covered="1567" line-rate="0.952" branches-covered="0"
          branches-valid="0" branch-rate="0" complexity="0">
```
- **line-rate = 0.952 (≈95%)**, lines-valid=1646, lines-covered=1567. Consistente con T31.

### 1.3 Cobertura frontend `frontend/coverage/lcov.info` — OK (LCOV no vacío)
- Ruta: `Etapa 3/Kiro/frontend/coverage/lcov.info` · existe · tamaño 19411 bytes · modificado 2026-11-17 13:59:26.
- Primeras líneas (real):
```
TN:
SF:src\App.tsx
FN:1,(empty-report)
FNF:1
FNH:0
FNDA:0,(empty-report)
```

### 1.4 Coincidencia de rutas de cobertura del template T4 — OK
El template T4 declara (rutas relativas al raíz del proyecto escaneado `Etapa 3/Kiro/`):
- `sonar.python.coverage.reportPaths=backend/coverage.xml` → existe ✔
- `sonar.javascript.lcov.reportPaths=frontend/coverage/lcov.info` → existe ✔

Ambas rutas resuelven a los reportes reales generados en T31. **Coinciden.**

### 1.5 Imágenes Docker congeladas disponibles — OK
```
sdd-sonarqube:frozen      4905574ab858   2.54GB
sdd-sonar-scanner:frozen  a3f421507670   1.45GB
```
(El contenedor `sonarqube` está corriendo y sirviendo en :9000; ver 1.1.)

### 1.6 Precondiciones que impiden el escaneo desatendido (esperado)
- `sonar-scanner` **no** está en PATH (existe la imagen `sdd-sonar-scanner:frozen`).
- **No** hay `SONAR_TOKEN` en el entorno; **no** hay script runner en el repo.
- → El escaneo autenticado es **ejecutado por el investigador**.

---

## 2. Configuración del escáner lista para ejecutar (staged)

- **Ubicación staged:** `Etapa 3/Kiro/sonar-project.properties`
- **Origen:** copia VERBATIM del template T4
  `_experiment_logs/Kiro/sonarqube/20261116-154624_T4_sonar-project.properties.template`.
- **Confirmación de identidad (SHA256) — idéntico a T4:**
  `0FA9D77A02315D5D1E63C13C7ADAE6866D4492B0642D188FE240C24399F2F3C7`
- **projectKey / alcance / exclusiones SIN cambios**, de modo que el PRE (T32) y
  el final (T35) sean comparables 1:1:
  - `sonar.projectKey=shift-bank-stage3-kiro`
  - `sonar.sources=backend/app,frontend/src`
  - `sonar.python.coverage.reportPaths=backend/coverage.xml`
  - `sonar.javascript.lcov.reportPaths=frontend/coverage/lcov.info`
  - exclusiones/tests/cpd ya definidas en el template.

---

## 3. Comandos EXACTOS que debe ejecutar el investigador (elegir UNA opción)

> **Precondición en el momento del escaneo** (ya satisfecha ahora por T31):
> deben existir `backend/coverage.xml` y `frontend/coverage/lcov.info`.
> La importación de cobertura ya está declarada en `sonar-project.properties`
> (no hace falta pasarla por línea de comandos).
> `<RESEARCHER_TOKEN>` lo provee el investigador — NO está en este repo.

### Opción (a) — Scanner dockerizado con la imagen congelada `sdd-sonar-scanner:frozen`

El contenedor del scanner debe (i) montar el raíz del proyecto `Etapa 3/Kiro`
como directorio de trabajo, y (ii) poder alcanzar el SonarQube del host en `:9000`.

**En Docker Desktop (Windows / macOS)** — usar `host.docker.internal` para llegar al host:
```powershell
docker run --rm `
  -e SONAR_HOST_URL="http://host.docker.internal:9000" `
  -e SONAR_TOKEN="<RESEARCHER_TOKEN>" `
  -v "C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\Kiro:/usr/src" `
  sdd-sonar-scanner:frozen `
  -Dsonar.host.url=http://host.docker.internal:9000 `
  -Dsonar.token=<RESEARCHER_TOKEN>
```

**En Linux** — usar `--network host` y `http://localhost:9000`:
```bash
docker run --rm \
  --network host \
  -e SONAR_HOST_URL="http://localhost:9000" \
  -e SONAR_TOKEN="<RESEARCHER_TOKEN>" \
  -v "/ruta/al/repo/Etapa 3/Kiro:/usr/src" \
  sdd-sonar-scanner:frozen \
  -Dsonar.host.url=http://localhost:9000 \
  -Dsonar.token=<RESEARCHER_TOKEN>
```

Notas de red (documentación precisa):
- `sdd-sonar-scanner:frozen` usa `/usr/src` como workdir por defecto; por eso se
  monta el raíz del proyecto ahí y el scanner lee `sonar-project.properties` staged.
- En Docker Desktop, un contenedor NO alcanza el `:9000` del host vía `localhost`;
  debe usar `host.docker.internal`. `--network host` **no** funciona igual en
  Docker Desktop (Windows/macOS) → por eso allí se usa `host.docker.internal`.
- En Linux nativo, `--network host` comparte la red del host y `localhost:9000` sí funciona.

Para capturar el log del scanner (ver §4), redirigir stdout/stderr, p. ej. en PowerShell:
```powershell
docker run ... sdd-sonar-scanner:frozen -Dsonar.host.url=... -Dsonar.token=... *> `
  "C:\...\Etapa 3\_experiment_logs\Kiro\sonarqube\<TS>_T32_PRE_scanner.log"
```

### Opción (b) — CLI nativo `sonar-scanner` (si el investigador lo instala)

Desde el raíz del proyecto `Etapa 3/Kiro` (donde está el `sonar-project.properties` staged):
```powershell
# cwd = Etapa 3\Kiro
sonar-scanner `
  -Dsonar.host.url=http://localhost:9000 `
  -Dsonar.token=<RESEARCHER_TOKEN>
```
- No hace falta repetir projectKey/sources/coverage: están en `sonar-project.properties`.
- Capturar log: añadir `*> <ruta>\<TS>_T32_PRE_scanner.log`.

---

## 4. Evidencia cruda a EXPORTAR/PRESERVAR tras el escaneo (sin sobrescribir)

Destino: `Etapa 3/_experiment_logs/Kiro/sonarqube/` — usar prefijo de timestamp
`<TS>` único por artefacto, **NO sobrescribir** nada existente (incluido el
template T4 ni este registro de preparación). Lista exacta:

1. **Config usada:** copia del `sonar-project.properties` realmente usado →
   `<TS>_T32_PRE_sonar-project.properties`.
2. **Log/stdout del scanner:** salida completa del comando (Opción a o b) →
   `<TS>_T32_PRE_scanner.log`. Debe contener el enlace al informe y el **ce task id**.
3. **Analysis ID / CE task id:** del log del scanner ("More about the report
   processing at .../api/ce/task?id=<CE_TASK_ID>"). Consultar y guardar:
   - `GET http://localhost:9000/api/ce/task?id=<CE_TASK_ID>` →
     `<TS>_T32_PRE_ce_task.json` (contiene `analysisId`).
4. **Lista de issues (JSON):**
   - `GET http://localhost:9000/api/issues/search?componentKeys=shift-bank-stage3-kiro&ps=500`
     (paginar con `&p=2,3,...` si `total` > 500) →
     `<TS>_T32_PRE_issues.json`.
5. **Quality Gate (JSON):**
   - `GET http://localhost:9000/api/qualitygates/project_status?projectKey=shift-bank-stage3-kiro`
     → `<TS>_T32_PRE_quality_gate.json`.
6. **Reportes de cobertura usados (copias):**
   - `backend/coverage.xml`  → `<TS>_T32_PRE_backend_coverage.xml`
   - `frontend/coverage/lcov.info` → `<TS>_T32_PRE_frontend_lcov.info`
   (Los originales en `Etapa 3/Kiro/...` **no** deben borrarse.)

Opcional recomendado (refuerza la comparabilidad 1:1 con T35):
- `GET http://localhost:9000/api/measures/component?component=shift-bank-stage3-kiro&metricKeys=coverage,line_coverage,ncloc,bugs,vulnerabilities,code_smells,duplicated_lines_density`
  → `<TS>_T32_PRE_measures.json`.

Todas las llamadas `GET` autenticadas usan la cabecera `Authorization: Basic`
con el token como usuario (contraseña vacía) o `-u <RESEARCHER_TOKEN>:` en curl.

---

## 5. Gate del investigador (T33)

El escaneo autenticado queda **DIFERIDO al investigador** (no ejecutado;
nada fabricado). Tras ejecutar la Opción (a) o (b) y preservar los artefactos
de §4 sin sobrescribir, procede el **gate T33** para validar que:
- el PRE-scan se completó con cobertura importada (backend + frontend),
- los artefactos crudos quedaron preservados en
  `Etapa 3/_experiment_logs/Kiro/sonarqube/`,
- la configuración usada es idéntica a la de T4/T35 (comparación 1:1).

**T32 permanece BLOQUEADA/DETENIDA hasta la ejecución del investigador. No es PASS.**
