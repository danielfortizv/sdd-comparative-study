# Preparación de Stage 3 — Shift Bank / Tessl

**Fecha:** 2026-11-13  
**Estado:** preparación completada; listo para iniciar Stage 3 cuando se aprueben la semilla común y la opción funcional.

## Alcance y estado de origen

- **Origen:** `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 2\Tessl`
- **Destino:** `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\Tessl`
- **Evidencia:** `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\_experiment_logs\Tessl`
- Se copió el estado actual de Stage 2, que tenía 34 entradas en `git status` al inicio de la inspección. No se modificaron los archivos de origen ni sus evidencias.
- La copia conserva la aplicación y sus especificaciones existentes: transferencias ACH/interbancarias, pagos recurrentes y límites dinámicos, además de las funciones bancarias previas. Se preservaron los siete archivos de especificación presentes, pruebas, configuraciones, dependencias, instrucciones de agentes y el plugin Tessl vendorizado.

## Copia, integridad y exclusiones

- Se inventariaron **5.720 archivos**: **82 incluidos** y **5.638 excluidos**. Los **82 archivos copiados coinciden** con Stage 2 por SHA-256; hubo **0 diferencias**.
- El detalle por archivo está en [`E3_TESSL_BASELINE_SHA256.csv`](./E3_TESSL_BASELINE_SHA256.csv) y el inventario completo de incluidos/excluidos en [`E3_TESSL_FILE_INVENTORY.csv`](./E3_TESSL_FILE_INVENTORY.csv). El registro estructurado está en [`E3_TESSL_BASELINE_METADATA.json`](./E3_TESSL_BASELINE_METADATA.json).
- Se excluyeron `node_modules`, `dist`, cachés de pytest y Python, archivos de bytecode, artefactos temporales y la base SQLite mutable. El inventario registra cada archivo excluido y su motivo. Las dependencias del frontend se instalaron después en Stage 3, dentro de `frontend\node_modules`.
- La base Stage 2 `shift_bank.db` (94.208 bytes) pasó `PRAGMA integrity_check` (`ok`) y contenía el estado inicial reproducible: 1 usuario, 2 cuentas, 3 transacciones, 1 límite y 1 estado MFA; no tenía transferencias, beneficiarios ni pagos recurrentes. `backend\app\main.py` crea el esquema e invoca `seed_initial_data`, por lo que la base no se copió. Las pruebas usaron `DATABASE_URL=sqlite://` en memoria y no generaron una base en Stage 3. Una lectura de hash posterior de la base de origen no fue posible porque otro proceso la mantenía abierta; no se intentó modificarla ni copiarla.

## Integración Tessl

- Se preservaron `tessl.json`, las reglas y el paquete vendorizado `tessl-labs/spec-driven-development` **2.0.1**, incluido el flujo **spec-before-code**.
- Se recrearon **16 junctions** bajo `.agents`, `.codex`, `.github` y `.vscode`; todos apuntan a los skills dentro de `Stage 3\Tessl\.tessl\plugins`. No hay junctions rotos ni destinos de Stage 1/2.
- La revisión de la configuración e instrucciones de integración no encontró referencias a Stage 1 o Stage 2.

## Versiones y dependencias

| Herramienta / paquete | Versión observada |
|---|---:|
| Tessl CLI | 0.118.1 |
| Plugin Tessl SDD | 2.0.1 |
| Gemini CLI | 0.65.0 (solo se consultó la versión; no se usó para desarrollo funcional) |
| Python / pytest | 3.13.2 / 9.1.1 |
| FastAPI / Uvicorn | 0.142.2 / 0.54.0 |
| Pydantic / SQLAlchemy / httpx | 2.12.5 / 2.1.6 / 0.28.1 |
| Node.js / npm | 20.17.0 / 11.6.3 |

- Frontend: `npm ci` terminó con código 0 usando el `package-lock.json` copiado (lockfile v3), exclusivamente dentro de Stage 3. npm reportó **5 vulnerabilidades** en el árbol bloqueado (2 moderadas, 1 alta y 2 críticas); no se actualizaron dependencias ni se aplicó una corrección.
- Backend: no existe lockfile; solo `backend\requirements.txt`. Sus dependencias ya estaban disponibles en el entorno Python observado, así que no se instaló un conjunto no bloqueado ni se cambió ese entorno. Las versiones utilizadas se registraron arriba.
- El primer intento de `npm ci` fue interrumpido al tratar PowerShell una advertencia de stderr como error; el segundo intento terminó correctamente. Ambos registros están conservados.

## Regresión ejecutada

Cada suite se ejecutó **una vez** desde Stage 3.

| Suite | Resultado | Observaciones |
|---|---|---|
| Backend — `python -m pytest backend\tests -v` | Código 0; **43 passed** | Dos advertencias deprecadas. El scheduler en segundo plano también registró errores SQLite `no such table: transfers` al usar SQLite en memoria entre hilos; no fallaron aserciones. No se modificó código para ocultar el problema. |
| Frontend — `npm test` (`vitest run`) | Código 0; **6 archivos, 35 tests passed** | Se observaron advertencias React `act(...)` en pruebas de `RecurringPayments`. |

Los registros están en [`E3_TESSL_REGRESION_BACKEND.txt`](./E3_TESSL_REGRESION_BACKEND.txt), [`E3_TESSL_REGRESION_BACKEND_RAW.txt`](./E3_TESSL_REGRESION_BACKEND_RAW.txt), [`E3_TESSL_REGRESION_FRONTEND.txt`](./E3_TESSL_REGRESION_FRONTEND.txt) y [`E3_TESSL_REGRESION_FRONTEND_RAW.txt`](./E3_TESSL_REGRESION_FRONTEND_RAW.txt). Los antiguos registros “iniciales” de Stage 2 no se usaron como resultado final porque anteceden a la implementación actual.

## Desviaciones, pendientes y restricciones respetadas

- No se modificaron funcionalidad, especificaciones ni pruebas; Stage 1 y Stage 2 no fueron destinos de instalación o ejecución de pruebas.
- No se creó `SEED-3.md`, no se inicializaron especificaciones nuevas de Stage 3 y no se seleccionó una opción funcional.
- Quedan para revisión posterior: los errores del scheduler observados durante la suite backend, las advertencias React/deprecaciones, las vulnerabilidades reportadas por npm y la ausencia de lockfile backend.
- La preparación queda detenida aquí, a la espera de la aprobación de la semilla experimental común y de la opción funcional para Stage 3.

## Evidencia operativa adicional

- Copia: [`E3_TESSL_COPIA_ROBOCOPY.txt`](./E3_TESSL_COPIA_ROBOCOPY.txt)
- Instalación frontend: [`E3_TESSL_NPM_CI_ATTEMPT_02.txt`](./E3_TESSL_NPM_CI_ATTEMPT_02.txt) y [`E3_TESSL_NPM_CI.txt`](./E3_TESSL_NPM_CI.txt)
