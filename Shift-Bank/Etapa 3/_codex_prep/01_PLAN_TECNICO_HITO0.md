# 01 — Plan técnico ejecutable de Codex para Hito 0

**Mandato:** configurar y verificar la línea base E3 antes del primer prompt de Gemini. Ejecutar los pasos en orden, con evidencia cruda, sin crear nuevas funcionalidades ni especificaciones.

## Fase 0. Preflight de seguridad — SIN escritura en fuentes

1. Resolver `REPO_ROOT`, `SOURCE_E2`, `SOURCE_E2_LOGS`, `DEST_E3`, `DEST_E3_LOGS`, `CODEX_INPUT` y `SEED_E3` desde `00_CONTEXTO_Y_CONTRATOS.md` con rutas absolutas canónicas.
2. Leer `README_COMO_USAR.md`, `00_...`, `01_...`, `02_...`, `03_...`, `CHECKLIST_ENTREGA.md`, `SEED-3.md` y el informe E2 de cierre si existe. Registrar archivos ausentes.
3. Inspeccionar `SOURCE_E2` y la estructura real: `backend`, `frontend`, `specs`, `.specify`, manifiestos, `pyproject.toml`/`requirements*.txt`, `package-lock.json`, `.gitignore`, `conftest.py` y configuración del backend. Verificar que **no se está trabajando accidentalmente en Tessl u otra variante**.
4. Inspeccionar `DEST_E3` **antes de copiar**. Si ya tiene código no idéntico, modificaciones humanas, bases de datos, secretos, evidencia o trabajos E3 anteriores: **NO sobrescribir, NO fusionar, NO limpiar**. Reportar `NO-GO: destination collision` y detener las operaciones de escritura (sí se permite emitir un diagnóstico en evidencia si el directorio ya estaba autorizado y no requiere sobrescritura).
5. Detectar archivos SQLite históricos y sidecars (`.db`, `.sqlite`, `.sqlite3`, `-wal`, `-shm`) por **nombres y metadatos**, sin abrirlos como base activa, eliminarlos ni forzar checkpoint. No incluir en la copia.
6. Leer el estado Git **sin modificar Git**: `git rev-parse --show-toplevel`, `git branch --show-current`, `git rev-parse HEAD`, `git status --porcelain=v1 -uall` (captura íntegra o fragmento justificado); el monorepo puede estar sucio por proyectos ajenos. Documentar solo los cambios que corresponden al alcance.
7. Identificar riesgo de credenciales o datos sensibles (no incluir valores secretos en reportes). Si se encuentran en E2, registrar solamente **ruta y clasificación**, no copiar ni imprimir contenido.

## Fase 1. Instalar semilla sin modificarla

- Asegurar que `Shift-Bank/Etapa 3/SEED-3.md` existe con el contenido **idéntico** a la semilla suministrada, cuyo SHA-256 es `99d23b7aee6eeb775fdc1617fff46a5409f10cb779ebcf411245e4602fabf1d9`.
- Si falta, copiar el archivo **byte a byte** desde `CODEX_INPUT/SEED-3.md`; después verificar el hash.
- Si existe y su hash **difiere**, detenerse y reportar conflicto. No regenerar, «normalizar» saltos de línea, reformatear, añadir encabezados o sobrescribir.

## Fase 2. Inventario E2 antes de la copia

- Identificar cómo se definió el inventario de **74 archivos durables E2**. Revisar si existe `SOURCE_E2_LOGS/E2_SPECKIT_FINAL_MANIFEST_SHA256.csv` y su encabezado real. Usar exactamente el mismo criterio o documentar la diferencia; no suponer columnas.
- Congelar inventario reproducible **antes** de copiar: rutas relativas, clasificación, tamaño, SHA-256; orden lexicográfico estable y serialización CSV UTF-8 (preferiblemente con BOM solo si así lo usa el estudio, y registrar el formato). Excluir artefactos no durables con patrón explícito.
- Comprobar si el inventario recién calculado concuerda con el manifiesto histórico; si existe divergencia, reportar rutas exactas y **detener la copia** hasta revisión, salvo que la divergencia sea exclusivamente un filtro de archivos diferente y esté demostrada documentalmente.
- Evitar que la herramienta dependa únicamente de `LastWriteTime`/tamaño para concluir integridad. Comparar **SHA-256 reales**.

## Fase 3. Crear copia independiente E3

- Copiar exclusivamente **archivos fuente durables de E2 de la misma herramienta**, preservando rutas y bytes. Deben entrar los módulos backend, frontend, manifestos/locks, tests, especificaciones de E1/E2, `.specify`/scripts/plantillas pertinentes, `.gitignore` y configuración SDD nativa.
- Excluir **al copiar**: `.git`, `.venv`, `venv`, `node_modules`, `dist`, `build`, `.pytest_cache`, `.ruff_cache`, `__pycache__`, `coverage`, `.coverage*`, `.scannerwork`, `.sonar`, logs, sesiones JSONL, temporales, archivos editor/IDE efímeros, bases SQLite y sidecars, secretos/certificados y `.env*`. No copiar datos experimentales antiguos al árbol de código de E3.
- No usar `robocopy /MIR` ni otro modo espejo destructivo. No seguir enlaces simbólicos que apunten a archivos fuera del origen autorizado; registrar symlinks y solicitar aprobación si son necesarios para la ejecución.
- **No editar los specs heredados**: los documentos `specs/001-...` y `specs/002-...` deben seguir siendo históricamente E1/E2. No crear `specs/003-...`, `AGENTS.md` de proyecto ni `sonar-project.properties` nuevo por iniciativa de Codex.
- Si la ruta E3 ya contiene una copia íntegra byte a byte, se permite verificarla y reutilizarla sin escribir. Si existe una copia parcial, no «arreglarla» fusionando por suposición: reportar y parar.
- Emitir inventario **post-copia** y una matriz de igualdad fuente→destino: conteo, rutas, SHA, tamaño, ausentes, modificados, extras; conservar el detalle y resumen. **Gate:** cero diferencias en archivos durables heredados. Los documentos de instrucciones Codex permanecen fuera del código de E3.

## Fase 4. Registrar versiones y configuración antes de Gemini

Comprobar, sin instalar ni alterar globales:

- Windows y arquitectura, versión PowerShell; Python y pip, versiones de FastAPI, pytest y uvicorn **en el entorno efectivo**; Node.js, npm; Docker Engine/Compose si están disponibles (solo `--version` / `info`, no correr contenedores); Git.
- Gemini CLI `gemini --version`, modelo efectivo (puede variar por sesión, no inferir del nombre de un modelo mostrado en logs), Spec Kit CLI/comandos/skills nativos y configuración `.specify`; Codex actual y rama Git. Registrar `N/D` si no se pudo comprobar.
- Verificar estado de `SONAR_TOKEN` solo mediante presencia/ausencia, **nunca valor**; no ejecutar SonarQube en Hito 0.
- Inventariar referencias absolutas de E2 que **podrían** requerir modificación autorizada en fases posteriores, pero no sustituirlas ahora; distinga rutas semánticas de rutas durables de código. No crear configuración del modelo ni defaults de seguridad.

## Fase 5. Instalar dependencias aisladas si es necesario

- Para backend, preferir un `venv` **nuevo dentro de E3** con la versión Python del proyecto. Instalar a partir de los manifests heredados, respetando versiones fijadas; no editar `requirements`, `pyproject`, `uv.lock` u otros archivos fuente.
- Para frontend, usar `npm ci` **si existe un lockfile compatible**; no usar `npm install` para reescribir `package-lock.json` silenciosamente. Registrar red, dependencias y conflictos sin improvisar una versión diferente.
- Si la instalación necesita red y falla, registrar código/salida; marcar `NO-GO` para pruebas no ejecutadas y detener la cadena de verificaciones dependientes. No instalar `Gemini`, `Spec Kit`, `Node`, `Docker`, `SonarScanner` globalmente durante este mandato.
- Las dependencias/cachés creados en E3 quedan excluidos del inventario durable y las métricas de LOC.

## Fase 6. Regresión de herencia en E3, con DB desechable

1. Inspeccionar cómo la app descubre `SHIFT_BANK_DB_PATH`, cómo `backend/tests/conftest.py` configura el aislamiento y si la inicialización abre SQLite automáticamente. Antes de importar cualquier módulo backend, fijar una variable de entorno a **una ruta desechable dentro de E3**, distinta de todas las DB preservadas.
2. No asumir que los tests son seguros solo por tener fixture. Corroborar en código que ninguna prueba llama `init_db()` o habilita workers contra `SOURCE_E2/backend/shift_bank.db` ni contra `DEST_E3/backend/shift_bank.db` si esta ruta es preservada.
3. Ejecutar en copia E3 (si el entorno está listo) las verificaciones **en procesos independientes**, guardando STDOUT, STDERR, comando, directorio de trabajo, variable de aislamiento **sin su secreto**, timestamp, duración, exit code y conteos reales:

   ```powershell
   # Referencias de comandos: Codex debe resolver venv, cwd y env correctos.
   python -m pytest backend/tests -q
   npm --prefix frontend test -- --run
   npm --prefix frontend run build
   ```

4. **Valores esperados de E2, solo como comparación:** 47 pytest y 12 Vitest aprobados y build limpio. Si hay 46/47, 13/13 o cualquier otro resultado, **reportar la diferencia real**, sin modificar tests para forzar 47/12 y sin declarar PASS falso.
5. Mantener `ENABLE_TEST_ENDPOINTS=false` para cualquier verificación interactiva fuera de pruebas unitarias; evitar lanzar servidores persistentes o abrir la UI salvo que resulte estrictamente necesario y quede registrado. No hacer pruebas de carga, despliegue, SonarQube, instalación Docker ni tests contra bancos externos.
6. Al terminar las pruebas, recalcular SHA-256 de **los archivos durables de E3**. Deben seguir coincidiendo byte a byte con E2. Si tests/build alteran fuentes, lockfiles o especificaciones, guardar el delta exacto, marcar `NO-GO` y **no revertir ni «normalizar» unilateralmente**; solicitar revisión.

## Fase 7. Preparar estructura para evidencia futura (sin crear resultados falsos)

Crear bajo `DEST_E3_LOGS` solamente:

```text
preparacion/
  E3_SPECKIT_HITO0_READINESS.md
  E3_SPECKIT_SOURCE_E2_MANIFEST_SHA256.csv
  E3_SPECKIT_COPY_E3_MANIFEST_SHA256.csv
  E3_SPECKIT_COPY_COMPARISON.csv
  E3_SPECKIT_GIT_STATE.txt
  E3_SPECKIT_ENVIRONMENT.txt
  E3_SPECKIT_ISOLATION.md
  E3_SPECKIT_PREPARACION_CODEX_LOG.md
  checksums/                # opcional: manifest de evidencias generadas
sesiones/
decisiones/
pruebas/
  E3_SPECKIT_PYTEST_PRE.txt
  E3_SPECKIT_VITEST_PRE.txt
  E3_SPECKIT_BUILD_PRE.txt
locust/
sonarqube/
diffs/
```

- Los archivos `pruebas/*_PRE.txt` se crean **solo al ejecutar la prueba**; si se bloquea, registrar `NOT EXECUTED` en readiness y no crear un log que simule ejecución.
- La carpeta `sesiones/` inicia vacía hasta la primera sesión Gemini E3. No copiar sesiones E2.
- La carpeta `decisiones/` inicia vacía; NO prellenar decisiones de E3 copiando de Tessl.
- Las demás carpetas pueden estar vacías. No generar falsos CSV de carga, cobertura, SonarQube, requisitos ni resultados.
- Para `SEED-3.md` registrar hash, ruta y procedencia sin agregar comentarios al archivo.

## Fase 8. GO / NO-GO y parada

Crear `preparacion/E3_SPECKIT_HITO0_READINESS.md` con:

1. Fuente E2 verificada y número/hash de archivos heredados.
2. Semilla E3 verificada por hash.
3. Destino E3 preparado, código aislado e intacto.
4. Estado Git, versiones reales de CLI/entorno y bloqueos.
5. Comandos, exit codes y conteos de regresiones; los logs crudos separados.
6. DBs preservadas y estrategia de aislamiento; confirmar el **alcance real de la comprobación** (hash antes/después cuando sea posible).
7. Diferencias y limitaciones, incluyendo discrepancias con las cifras reportadas de E2.
8. **Veredicto:** `GO PARA GEMINI HITO 1` únicamente si no hay colisión, SHA correcto, herencia intacta y verificaciones principales ejecutadas sin fallos; en caso contrario `NO-GO` con la acción mínima necesaria.
9. Puerta de autorización: **no iniciar E3 Hito 1 ni editar E3 specs/código sin aprobación humana**.

Detener Codex inmediatamente después del reporte y dar un resumen compacto al usuario. Si existe un bloqueo, detenerse en esa fase: no sortearlo alterando el experimento.
