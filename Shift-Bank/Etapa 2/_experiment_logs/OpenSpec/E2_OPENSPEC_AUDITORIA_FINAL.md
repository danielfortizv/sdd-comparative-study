# Shift Bank E2 — Auditoría funcional final (OpenSpec)

Fecha: 2026-11-16 (America/Bogota). No se ejecutó un nuevo análisis SonarQube.

## Resultado ejecutivo

- Se corrigió una brecha confirmada de interfaz: los estados ACH y de ejecuciones recurrentes quedaban obsoletos mientras la aplicación permanecía abierta, aunque el procesador backend ya hubiera actualizado el estado. La interfaz ahora vuelve a consultar periódicamente y conserva los valores no guardados del formulario de límites.
- Se añadió una prueba de conservación de saldo total para transferencias internas.
- Verificación final: compilación Python PASS; 22 pruebas backend PASS; 5 pruebas frontend PASS; build de producción PASS; validación OpenSpec strict PASS.
- No se ejecutaron pruebas de navegador ni prueba visual manual.
- Las descripciones canónicas A01–A21 no aparecen en los artefactos OpenSpec accesibles ni en la evidencia OpenSpec consultada. La matriz siguiente es una correspondencia de auditoría por áreas, no certifica el orden de los IDs contra el contrato común externo.

## Matriz A01–A21

| ID | Área de verificación usada para esta matriz | Estado | Evidencia |
|---|---|---|---|
| A01 | Datos Stage 1: cuentas, saldos y migración sin reseed | PASS | test_stage1_database_migrates_without_reseeding_or_losing_history; test_repeatable_migration_preserves_rows_and_settings; test_http_routes_preserve_stage1_and_expose_stage2 |
| A02 | Transferencia interna y conservación monetaria | PASS | Nuevo test_internal_transfer_conserves_total_balance; test_history_filters_include_internal_counterparty_and_external_debit_only |
| A03 | Rechazo por fondos insuficientes aislado del límite | PASS | test_insufficient_funds_isolated_from_transfer_limit; test_ach_insufficient_funds_rejects_before_acceptance |
| A04 | Configuración y valores por defecto de límites | PASS | test_amount_precision_and_limits_boundaries; test_invalid_limit_update_preserves_saved_values_and_reduction_is_immediate; test API |
| A05 | Rechazo de límites inválidos y precisión monetaria | PASS | test_invalid_limit_update_preserves_saved_values_and_reduction_is_immediate; test_amount_precision_and_limits_boundaries; prueba frontend de validación |
| A06 | Límites exactos y capacidad diaria | PASS | test_amount_precision_and_limits_boundaries |
| A07 | Transferencia interna contabilizada una sola vez | PASS | test_internal_transfer_counts_once_and_mfa_revalidates |
| A08 | Atribución UTC de transferencia interna autorizada por MFA | PASS | test_internal_mfa_completion_across_utc_midnight_uses_completion_date |
| A09 | MFA heredada: no débito antes de autorización, reintento y expiración | PASS | test_internal_transfer_counts_once_and_mfa_revalidates; test_ach_mfa_wrong_code_retry_expiry_and_daily_limit_revalidation; test_abandoned_mfa_records_expire_without_confirmation; prueba API |
| A10 | Beneficiarios guardados, datos y formatos | PARTIAL | test_beneficiary_validation_and_snapshot cubre validación, actualización, eliminación y snapshot; prueba API cubre creación. No hay una aserción directa de listado/CRUD completo en una prueba |
| A11 | Destinatario ACH ad hoc y rechazo antes de aceptación | PASS | test_ach_insufficient_funds_rejects_before_acceptance; test_sensitive_ach_no_debit_until_mfa_then_settles_without_debit; test_history_filters_include_internal_counterparty_and_external_debit_only |
| A12 | ACH aceptado: pendiente y débito inmediato | PASS | test_sensitive_ach_no_debit_until_mfa_then_settles_without_debit; test_ach_pending_settlement_failure_once_and_midnight_usage |
| A13 | Liquidación ACH a 30 segundos, timestamp y sin débito duplicado | PASS | test_sensitive_ach_no_debit_until_mfa_then_settles_without_debit; usa reloj controlado y llamadas al procesador, no espera 30 segundos reales |
| A14 | Fallo ACH determinista, reembolso único e idempotencia | PASS | test_ach_pending_settlement_failure_once_and_midnight_usage |
| A15 | Fallo ACH tras medianoche UTC y corrección del día original | PASS | test_ach_pending_settlement_failure_once_and_midnight_usage |
| A16 | Historial ACH, contraparte externa y filtros de cuenta | PASS | test_beneficiary_validation_and_snapshot; test_history_filters_include_internal_counterparty_and_external_debit_only; prueba API |
| A17 | Frecuencias recurrentes, cadencia UTC y primera ejecución | PASS | test_schedule_anchor_controls_and_rec_d03; test_schedule_frequency_mfa_revalidation_failures_and_restart_skip; test_recurring_ach_is_one_history_entry_and_settlement_updates_occurrence |
| A18 | MFA de creación recurrente, revalidación y REC-D03 | PASS | test_schedule_anchor_controls_and_rec_d03; test_schedule_frequency_mfa_revalidation_failures_and_restart_skip; test_abandoned_mfa_records_expire_without_confirmation |
| A19 | Pausa, reanudación, cancelación terminal y ocurrencias saltadas | PASS | test_schedule_anchor_controls_and_rec_d03; test_schedule_frequency_mfa_revalidation_failures_and_restart_skip |
| A20 | Fallos recurrentes, avance, reinicio e idempotencia | PASS | test_recurring_execution_is_idempotent_and_failed_attempt_advances; test_recurring_limit_failure_is_recorded_without_debit; test_recurring_ach_is_one_history_entry_and_settlement_updates_occurrence |
| A21 | Interfaz Stage 2 y visibilidad de estados actualizados | PARTIAL | Pruebas Node de validación/polling y build TypeScript/Vite; no se ejecutó navegador ni prueba end-to-end visual |

Los estados reflejan evidencia para las áreas indicadas. Los IDs oficiales A01–A21 no pudieron cotejarse contra descripciones canónicas disponibles; no se consultó ni copió la implementación de otra herramienta.

## Defectos y correcciones

### Estados mostrados sin refresco

Hallazgo: después de enviar un ACH, la UI podía continuar mostrando pending aunque el backend ya lo hubiera liquidado o fallado. También afectaba ejecuciones recurrentes procesadas en segundo plano.

Corrección: se añadió refresco cada cinco segundos mientras la aplicación está montada, cancelado al desmontarse. El sondeo no reemplaza borradores no guardados en el formulario de límites. Se agregó una prueba automatizada para repetición y cancelación.

Archivos: frontend/src/App.tsx, frontend/src/refreshPolling.mjs, frontend/src/refreshPolling.d.mts, frontend/tests/validation.test.mjs.

### Conservación de saldos internos

Se añadió backend/tests/test_banking.py::test_internal_transfer_conserves_total_balance, que verifica saldos origen/destino y suma conservada para una transferencia con centavos. No se encontró discrepancia de saldo en la implementación auditada.

## SonarQube inicial

Se preservaron sin cambios los artefactos en ../_experiment_logs/OpenSpec/sonarqube/.

- Proyecto: Shift-Bank---Stage-2---OpenSpec
- Analysis ID: 74358b40-4391-4280-83df-9ae09061e287
- Quality Gate: OK
- Bugs: 5
- Code Smells: 41
- NCLOC: 1354
- Coverage: 0%
- Cognitive Complexity: 288

No se hizo análisis final. Los artefactos preservados incluyen métricas, gate, resumen, tarea y log de scanner, pero no detalle de issues. La API anónima de issues devolvió HTTP 401 y no había credencial SONAR disponible en el entorno. No fue posible identificar ni corregir individualmente los cinco bugs o 41 code smells. La brecha de UI anterior se corrigió por auditoría funcional; no se afirma que corresponda a un issue Sonar. No se hicieron refactors especulativos.

## Verificación final

Desde backend:
- .venv\Scripts\python.exe -m py_compile main.py database.py banking.py tests\test_banking.py tests\test_api.py — PASS.
- .venv\Scripts\python.exe -m unittest discover -s tests -v — PASS, 22 tests, 0 failures, 0 skipped. Usa bases SQLite temporales aisladas.

Desde frontend:
- npm.cmd test — PASS, 5 tests, 0 failures, 0 skipped.
- npm.cmd run build — PASS, TypeScript y Vite 5.4.21; 33 módulos transformados.

Desde la raíz OpenSpec:
- openspec.cmd validate stage2-banking-enhancements --strict — PASS, change válido.
- openspec.cmd status --change stage2-banking-enhancements — 4/4 artefactos completos; 22 tasks permanecen marcados completos.

## Archivos modificados en esta ronda

- backend/tests/test_banking.py — test de conservación de saldos internos.
- frontend/src/App.tsx — refresco periódico y sincronización selectiva del formulario de límites.
- frontend/src/refreshPolling.mjs — helper nuevo de sondeo cancelable.
- frontend/src/refreshPolling.d.mts — declaración TypeScript.
- frontend/tests/validation.test.mjs — test de polling y cancelación.
- ../_experiment_logs/OpenSpec/E2_OPENSPEC_AUDITORIA_FINAL.md — este registro.

No se modificaron especificaciones, backend de aplicación, datos runtime, dependencias ni evidencia histórica. No se ejecutó prueba de navegador, no se sincronizó ni archivó el cambio y no se creó commit.

## Limitaciones pendientes para el investigador

- Obtener acceso SonarQube autenticado de solo lectura para revisar los cinco bugs y 41 code smells antes del análisis final manual.
- Ejecutar prueba manual/browser end-to-end de los flujos frontend, en especial actualización visual de estados ACH/recurrencia y validaciones.
- Comparar esta matriz con descripciones oficiales A01–A21 si se facilita un artefacto común accesible. La matriz actual no asegura la correspondencia oficial.
- Al cierre no se conoce fallo de prueba o build. El análisis final SonarQube queda pendiente de ejecución manual por el investigador.
