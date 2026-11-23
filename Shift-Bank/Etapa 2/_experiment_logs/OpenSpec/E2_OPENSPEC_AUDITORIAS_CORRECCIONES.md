# Shift Bank E2 — Auditorías y correcciones finales

## Resultado
Se repitieron las verificaciones finales: 22 pruebas backend aprobadas, 5 pruebas frontend aprobadas, build de producción aprobado y validación OpenSpec strict aprobada. El change tiene 22/22 tareas completas. Las 91 especificaciones de aceptación no representan 91 pruebas ejecutadas. No se realizó prueba de navegador.

No se encontró localmente SHIFT_BANK_E2_CONTRATO_COMUN_Y_REFERENCIA_TESSL.md, sección 7. Esta evaluación usa el mapping autoritativo proporcionado por el investigador y reemplaza la matriz previa por áreas.

| ID | Caso oficial | Estado | Evidencia |
|---|---|---|---|
| A01 | Accounts and history | PASS | test_http_routes_preserve_stage1_and_expose_stage2; test_history_filters_include_internal_counterparty_and_external_debit_only; test_stage1_database_migrates_without_reseeding_or_losing_history |
| A02 | Internal transfer consistency | PASS | test_internal_transfer_conserves_total_balance |
| A03 | Saved ACH beneficiaries | PARTIAL | test_beneficiary_validation_and_snapshot valida creación, actualización y eliminación; test API crea. No prueba listado/consulta completa |
| A04 | Ad hoc ACH | PASS | test_sensitive_ach_no_debit_until_mfa_then_settles_without_debit; test_ach_pending_settlement_failure_once_and_midnight_usage |
| A05 | Routing validation including inline UI feedback | PARTIAL | Backend y helper validan formato; inline renderizado no observado en navegador |
| A06 | Destination account number validation | PASS | test_beneficiary_validation_and_snapshot; routing and account formats enforce their digit counts |
| A07 | Pending ACH and once-only debit/settlement | PASS | test_sensitive_ach_no_debit_until_mfa_then_settles_without_debit; test_ach_pending_settlement_failure_once_and_midnight_usage. Usa reloj/procesador controlados |
| A08 | Failed ACH and once-only refund | PASS | test_ach_pending_settlement_failure_once_and_midnight_usage, con reprocesamiento |
| A09 | Invalid monetary amounts | PASS | test_amount_precision_and_limits_boundaries; money values allow positive COP precision to two decimal places |
| A10 | Consult and update transfer limits | PARTIAL | test_invalid_limit_update_preserves_saved_values_and_reduction_is_immediate; API GET; interacción visual no observada |
| A11 | Per-transfer equality and rejection | PASS | test_amount_precision_and_limits_boundaries; test_internal_transfer_counts_once_and_mfa_revalidates |
| A12 | Exact isolated daily sequence 400+300+300+10 | PARTIAL | Hay tests de igualdad/exceso/reducción de límites; la secuencia exacta 400+300+300+10 no se ejecutó |
| A13 | Inherited MFA behavior | PASS | test_sensitive_ach_no_debit_until_mfa_then_settles_without_debit; test_ach_mfa_wrong_code_retry_expiry_and_daily_limit_revalidation; test_abandoned_mfa_records_expire_without_confirmation |
| A14 | MFA cannot override financial limits | PASS | test_internal_transfer_counts_once_and_mfa_revalidates; test_ach_mfa_wrong_code_retry_expiry_and_daily_limit_revalidation; test_recurring_limit_failure_is_recorded_without_debit |
| A15 | Daily recurrence starts after one full interval | PARTIAL | test_recurring_execution_is_idempotent_and_failed_attempt_advances exercises a daily due occurrence; no isolated assertion verifies no-start first-run time/no immediate execution |
| A16 | Exact weekly/monthly intervals | PASS | test_schedule_anchor_controls_and_rec_d03 verifies seven-day cadence; test_schedule_frequency_mfa_revalidation_failures_and_restart_skip verifies 30 days |
| A17 | Recurring internal/ACH execution | PASS | test_recurring_execution_is_idempotent_and_failed_attempt_advances; test_recurring_ach_is_one_history_entry_and_settlement_updates_occurrence |
| A18 | Pause/resume/terminal cancellation | PASS | test_schedule_anchor_controls_and_rec_d03; test_schedule_frequency_mfa_revalidation_failures_and_restart_skip |
| A19 | Failed recurring execution and next occurrence | PASS | test_schedule_frequency_mfa_revalidation_failures_and_restart_skip; test_recurring_limit_failure_is_recorded_without_debit |
| A20 | Stage 1/Stage 2 regression and frontend build | PASS | test_stage1_database_migrates_without_reseeding_or_losing_history; test_http_routes_preserve_stage1_and_expose_stage2; production build |
| A21 | Actual browser-based UI workflows | NOT EXECUTED | No browser-driven or manual browser observation |

Totals: 15 PASS, 5 PARTIAL, 0 FAIL, 1 NOT EXECUTED. A21 is not inferred from helper tests or source inspection.

## MFA cross-tool deviation
The historical common-contract A13 reference reflects a Tessl-specific MFA boundary. OpenSpec preserves Stage 1: MFA for COP 1,000,000 or more, inclusive; code 123456; inherited five-minute expiration and retry behavior. Tests exercise exactly COP 1,000,000. This is a documented cross-tool deviation, not a regression.

## Corrections confirmed
- Frontend periodic state refresh every five seconds while mounted, with timer cleanup; it does not overwrite an in-progress limits form. Regression test: status refresh polling repeats and can be stopped when the app unmounts.
- Added test_internal_transfer_conserves_total_balance for internal money conservation with fractional COP.
- Earlier implementation fixes are in E2_OPENSPEC_IMPLEMENTATION_LOG.md: REC-D03 check ordering, isolated test fixture/assertion repairs, and setup/tool command corrections.

## Limitations
A03/A05/A10/A12/A15 remain partial for the stated gaps. A21 remains unexecuted. Migration testing used a Stage 1-shaped temporary fixture; no historical runtime bank.db was available. Individual Sonar issue descriptions were not available, so no issue-specific corrections are claimed.
