# Bitácora de preparación Codex — reanudación HITO 0

**Etiqueta:** `CODEX_PREPARACION_HITO0`  
**Fecha:** 2026-11-15  
**Alcance:** recuperar y verificar la preparación existente; no iniciar Gemini ni HITO 1.

## Evidencia existente recuperada

- El cierre histórico E2 identifica la variante Spec Kit 1.0.6 y reporta 74 archivos durables, 47 pruebas backend, 12 frontend y build satisfactorio.
- La auditoría persistida del manifiesto E2 terminó `PASS` el `2026-11-15T23:31:56.408712+00:00`: 74 procesados, 74 matches, 0 ausentes, 0 discrepantes, 0 inseguros y 0 errores.
- La comparación inicial E2→E3 existente tiene 74 filas `MATCH`. El manifiesto de verificación posterior previo a esta reanudación también tiene 74 filas `MATCH`.
- La clasificación de extras tiene 8.444 entradas: 8.424 de dependencias, 12 caché/temporales, 3 de build, 3 de evidencia local y 2 bases SQLite/sidecars. Las dos bases E2 están clasificadas `EXCLUDE`.
- El log backend existente acredita `python -m pytest backend/tests -q`, código 0, `47 passed, 1 warning`, en `2026-11-15T18:49:40.0418118-05:00`–`18:49:51.7521919-05:00`. El `TEST_DB_PATH` registrado apunta a `Etapa 3\Spec Kit\backend\tests\test_shift_bank.db`.
- Los logs históricos de Vitest y build no eran PASS: registraban código 1 por `EPERM`, `lstat C:\Users\danie`, ejecutándose bajo `zorro\codexsandboxoffline`. No se reutilizaron como resultados exitosos.
- El primer readiness existente, `E3_SPECKIT_HITO0_READINESS.md`, refleja un intento anterior bloqueado por ausencia del paquete en aquella fecha. Se preserva sin cambios; este informe final aporta el estado actualizado.

## Verificaciones nuevas de esta reanudación

1. Recalculé, contra `E2_SPECKIT_FINAL_MANIFEST_SHA256.csv`, los SHA-256 de los 74 archivos durables actuales tanto en E2 como en E3. Resultado: E2 74/74; E3 74/74. El inventario resultante está en [E3_SPECKIT_RESUME_FINAL_SHA256_20261115_190641.csv](./E3_SPECKIT_RESUME_FINAL_SHA256_20261115_190641.csv).
2. Verifiqué otra vez el seed de entrada y `Etapa 3\SEED-3.md`: `99d23b7aee6eeb775fdc1617fff46a5409f10cb779ebcf411245e4602fabf1d9`.
3. Revisé `conftest.py` y `database.py` de E3. La suite configura `TEST_DB_PATH` a `backend\tests\test_shift_bank.db`; la prueba no usa las bases E2. El archivo temporal no existe después del teardown. No abrí ni inicié SQLite en E2.
4. Ejecuté desde PowerShell normal como `zorro\danie`, en `Etapa 3\Spec Kit\frontend`:
   - `npm.cmd run test -- --run`: código 0, Vitest 2.1.9, 12/12 pruebas aprobadas, inicio `2026-11-15T19:05:09.5152213-05:00`, fin `19:05:13.5364484-05:00`. Salidas: [stdout](./E3_SPECKIT_VITEST_RESUME_20261115_190509.stdout.txt), [stderr](./E3_SPECKIT_VITEST_RESUME_20261115_190509.stderr.txt), [metadatos](./E3_SPECKIT_VITEST_RESUME_20261115_190509.meta.txt).
   - `npm.cmd run build`: código 0; `tsc` y Vite 5.4.21 finalizaron, 32 módulos transformados, sin stderr, inicio `2026-11-15T19:05:19.0475301-05:00`, fin `19:05:22.2934247-05:00`. Salidas: [stdout](./E3_SPECKIT_BUILD_RESUME_20261115_190518.stdout.txt), [stderr](./E3_SPECKIT_BUILD_RESUME_20261115_190518.stderr.txt), [metadatos](./E3_SPECKIT_BUILD_RESUME_20261115_190518.meta.txt).
5. Recalculé los 74 hashes después de las comprobaciones frontend: 74/74 siguen coincidiendo en origen y destino. `node_modules` y `frontend\dist` son artefactos de entorno/build, no archivos durables heredados.
6. La semilla y configuración nativa `.specify`/Gemini se verificaron como heredadas; `specs/003-shift-bank-stage3` no existe.
7. Creé las carpetas que faltaban (`sesiones`, `decisiones`, `pruebas`, `locust`, `sonarqube` y `diffs`). Copié a `pruebas/` los logs crudos existentes de pytest/npm ci y las salidas exitosas de Vitest/build; cotejé sus SHA-256 con los originales: 8/8 matches. No agregué datos ficticios.

## Instalación npm reutilizada y advertencias

El registro persistente de npm `C:\Users\danie\AppData\Local\npm-cache\_logs\2026-11-15T23_49_00_906Z-debug-0.log` confirma `npm ci --no-audit --no-fund`, `cwd` en el frontend E3, Node 20.17.0, npm 11.6.3 y `verbose exit 0`. El stdout existente informa `added 304 packages in 5s`. El stderr existente advierte que `@testing-library/jest-dom@7.0.1` declara Node `>=22`; a pesar de ello, las pruebas y el build se aprobaron con Node 20.17.0.

## Errores de diagnóstico y alcance

- Los intentos previos de npm desde `zorro\codexsandboxoffline` fallaron con `EPERM` al hacer `lstat C:\Users\danie`; no se cambiaron ACL ni políticas. La ejecución normal como `zorro\danie` pudo invocar `npm.cmd` y ejecutar las verificaciones requeridas.
- Una primera consulta auxiliar de versiones Python inline falló por quoting (`SyntaxError`); se corrigió sin cambiar archivos usando `python -m pip show fastapi pytest uvicorn` y `python -m pytest --version`, ambos con código 0.
- La validación final de enlaces detectó una ruta relativa incorrecta al cierre E2; se corrigió antes de entregar y se repitió la validación.
- No se modificaron fuentes, especificaciones, tests, lockfiles, `.specify`, historial Git ni bases E1/E2. El estado inicial ya tenía numerosos archivos E2/E3 no rastreados; los artefactos creados aquí también quedan sin seguimiento. No se usó `git add` ni se confirmó ningún cambio.
- Las bases E2 se inspeccionaron solo por metadatos/hash, no como SQLite activa. Hashes observados: `backend\shift_bank.db` (53.248 bytes; `2026-11-14T14:05:47.2007867-05:00`; SHA-256 `D41503BF2563A35E1C73D941681204B83324864112185B0F38C4E0ACD72B66ED`) y `backend\manual_test_shift_bank.db` (53.248 bytes; `2026-11-15T16:59:29.3368072-05:00`; SHA-256 `188CDDA0215D0CB4F514F4F08088FE019233431C731312B2A976B8D3A6085411`). Sus `LastWriteTime` anteceden al pytest de las 18:49; no existe en este registro un hash histórico previo de dichas bases para afirmar una comparación criptográfica antes/después.
- No se ejecutó SonarQube, Locust, Docker deployment, Gemini ni ningún workflow Spec Kit. No se creó especificación Stage 3 ni implementación.

## Paquete de evidencia

El informe de readiness y el handoff son [E3_SPECKIT_HITO0_READINESS_FINAL.md](./E3_SPECKIT_HITO0_READINESS_FINAL.md) y [E3_SPECKIT_GEMINI_HANDOFF.md](./E3_SPECKIT_GEMINI_HANDOFF.md). Los datos de versiones y configuración están en [E3_SPECKIT_ENVIRONMENT_RESUME.txt](./E3_SPECKIT_ENVIRONMENT_RESUME.txt). Logs anteriores permanecen intactos.
