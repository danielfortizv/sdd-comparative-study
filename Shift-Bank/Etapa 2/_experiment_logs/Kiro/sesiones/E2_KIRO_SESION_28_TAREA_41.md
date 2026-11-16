# E2 · Kiro · Sesión de implementación 28 — Tarea 41

- **Fecha:** 2026-11-16
- **Tarea:** 41 — (verificación) Ejecutar la suite completa de aceptación de la Etapa 2
- **Fase:** G — Verificación final y evidencia experimental
- **Objetivo:** Ejecutar **todas** las pruebas de las Fases C (límites), D (ACH/beneficiarios) y
  E (recurrentes/scheduler); **mapear cada escenario de aceptación A01–A19** a la(s) prueba(s)
  que lo cubren y registrar los PASS/FAIL **reales** de pytest.
- **Alcance autorizado:** solo Tarea 41. Tarea de verificación/evidencia pura; **sin modificar
  código de producción** ni pruebas.
- **Estado final:** COMPLETED — A01–A19 cubiertos, 100 % PASS; suite completa verde.
- **Requisitos:** 1–14 · **Contrato:** A01–A19.

## Naturaleza de la tarea

Tarea puramente de **verificación**. No crea ni modifica código de aplicación ni pruebas. Se
limita a ejecutar las suites ya escritas (Fases A–F) y a consolidar la trazabilidad
escenario → prueba → resultado. Los escenarios A20 (build + suite completa) y A21 (inspección
manual del navegador) pertenecen a las Tareas 42 y 43 y quedan fuera del alcance de esta tarea.

## Entorno de ejecución

- Ejecutado desde `Etapa 2/Kiro/backend` con el intérprete del entorno virtual
  (`.venv\Scripts\python.exe`).
- **Python 3.13.2**, **pytest 8.3.4**, pluggy 1.7.0, plugin anyio 4.16.0.
- Pruebas sobre **DB SQLite temporales aisladas** (fixtures `app_client`/`isolated_db_path`);
  reloj inyectable `ManualClock` para los escenarios deterministas (recurrentes/settlement).

## Comandos ejecutados y resultados reales

1. **Suite completa (confirmación global):**
   `python -m pytest -q`
   → **220 passed, 1 warning in 14.81s** (exit 0). 220/220 PASS, 0 FAIL, 0 SKIP.

2. **Archivos de aceptación C/D/E + regresión de contrato/internas, verboso** (para registrar
   PASS/FAIL por prueba y mapear A01–A19):
   `python -m pytest tests/test_limits.py tests/test_ach.py tests/test_recurring.py
   tests/test_recurring_execution.py tests/test_recurring_api.py
   tests/test_recurring_verification.py tests/test_scheduler.py
   tests/test_regression_api_contracts.py tests/test_regression_internal_transfers.py -v`
   → **150 passed, 1 warning in 10.69s** (exit 0). 150/150 PASS, 0 FAIL, 0 SKIP.

### Desglose por archivo (todos PASS)

| Archivo | Dominio | Pruebas |
|---|---|---:|
| `tests/test_limits.py` | Fase C — límites dinámicos y concurrencia | 11 |
| `tests/test_ach.py` | Fase D — beneficiarios + ACH | 16 |
| `tests/test_recurring.py` | Fase E — creación/MFA/ciclo de vida | 37 |
| `tests/test_recurring_execution.py` | Fase E — ejecución durable y atómica | 18 |
| `tests/test_recurring_api.py` | Fase E — endpoints recurrentes | 14 |
| `tests/test_recurring_verification.py` | Fase E — verificación A15–A19/D06/una-vez | 20 |
| `tests/test_scheduler.py` | Fase E — scheduler de fondo | 8 |
| `tests/test_regression_api_contracts.py` | Historial unificado / contratos (A01) | 13 |
| `tests/test_regression_internal_transfers.py` | Internas heredadas (A02) | 12 |
| **Total (archivos verbosos)** | | **150** |

> La suite completa (220) incluye además arnés, esquema/migración, reloj, transacción, MFA
> heredada y cuentas, no listados arriba por no aportar escenarios A01–A19 adicionales.

## Mapa de aceptación A01–A19 → prueba(s) → resultado

Fuente de la tabla A→Requisitos: `requirements.md` §"Escenarios de aceptación (A01..A21)".
Todas las pruebas listadas **PASS** en la ejecución de arriba (exit 0).

| Esc. | Requisitos | Prueba(s) que lo cubren | Resultado |
|---|---|---|---|
| **A01** | 6.1, 6.2, 15.1, 15.5 | `test_ach.py::test_historial_unificado_internas_y_ach`; `test_regression_api_contracts.py::test_historial_estructura_y_campos`, `::test_historial_historicas_y_nueva`, `::test_internas_conservan_forma_sin_beneficiario` | PASS |
| **A02** | 6.2, 15.2 | `test_regression_internal_transfers.py::test_transferencia_interna_exitosa_sin_mfa`, `::test_debito_y_credito_correctos_y_total_preservado`, `::test_estructura_e_estados_del_historial_heredados` | PASS |
| **A03** | 1.1, 1.2 | `test_ach.py::test_crear_y_listar_beneficiario_enmascarado`, `::test_ach_beneficiario_guardado` | PASS |
| **A04** | 1.2, 1.3, 7.2 | `test_ach.py::test_ach_guardar_adhoc_en_la_operacion`, `::test_ach_bajo_umbral_pending_y_debita` (beneficiario ad hoc) | PASS |
| **A05** | 2.2, 2.4, 7.3 | `test_ach.py::test_validacion_routing` (8/no numérico rechazado, 9 aceptado) | PASS |
| **A06** | 2.3, 7.3 | `test_ach.py::test_validacion_cuenta` (3/18 rechazada, 4–17 aceptada) | PASS |
| **A07** | 3.5, 4.2, 4.3, 4.4, 6.1 | `test_ach.py::test_ach_bajo_umbral_pending_y_debita`, `::test_settlement_idempotente_sin_redebito`, `::test_settlement_no_elegible_antes_del_retardo`, `::test_historial_unificado_internas_y_ach` | PASS |
| **A08** | 3.6, 5.1, 5.2, 15.7 | `test_ach.py::test_fallo_reembolsa_una_sola_vez`, `::test_ach_sensible_pending_auth_sin_debito` | PASS |
| **A09** | 3.1, 3.8 | `test_ach.py::test_ach_rechaza_monto_invalido` | PASS |
| **A10** | 13.2, 13.3 | `test_limits.py::test_defaults_d01`, `::test_get_incluye_consumo_y_disponibilidad`, `::test_put_actualiza_y_aplica` | PASS |
| **A11** | 14.1, 14.4 | `test_limits.py::test_frontera_exacta_por_transferencia_permitida`, `::test_rechaza_sobre_limite_por_transferencia` | PASS |
| **A12** | 14.2, 14.3, 14.4 | `test_limits.py::test_consumo_diario_acumulado_a12` (400+300+300 OK, siguiente excede), `::test_frontera_exacta_diaria_permitida` | PASS |
| **A13** | 3.3, 15.4 | `test_ach.py::test_ach_sensible_pending_auth_sin_debito`, `::test_ach_confirmacion_mfa_activa_y_debita`; `test_regression_mfa.py` (suite MFA heredada, 14/14 en suite completa) | PASS |
| **A14** | 3.4, 14.1, 14.5 | `test_limits.py::test_pin_correcto_no_salta_limite_a14`; `test_ach.py::test_ach_respeta_limite_por_transferencia` | PASS |
| **A15** | 8.5, 10.1 | `test_recurring_verification.py::test_A15_diario_sin_fecha_corre_tras_un_dia`; `test_recurring.py::test_fecha_omitida_un_intervalo_diario` | PASS |
| **A16** | 8.2 | `test_recurring_verification.py::test_A16_frecuencia_semanal_mensual_7_30_dias[daily/weekly/monthly]`, `::test_A16_siguiente_fecha_avanza_por_intervalo[...]` | PASS |
| **A17** | 8.1, 10.1, 10.4 | `test_recurring_verification.py::test_A17_interno_ejecuta_actualiza_saldo_movimiento_fecha`, `::test_A17_ach_ejecuta_pending_debito_inmediato`; `test_recurring_execution.py::test_internal_ocurrencia_ejecuta_al_vencer`, `::test_ach_ocurrencia_ejecuta_pending_con_debito` | PASS |
| **A18** | 9.1–9.7, 12.2 | `test_recurring_verification.py::test_A18_pausado_no_corre`, `::test_A18_reanudado_vuelve_elegible_y_ejecuta`, `::test_A18_cancelado_es_terminal_no_reanudable_ni_ejecutable` | PASS |
| **A19** | 11.1, 11.2, 14.6 | `test_recurring_verification.py::test_A19_fondos_insuficientes_registra_failed_y_avanza_sin_debito`, `::test_A19_limite_excedido_registra_failed_y_avanza_sin_debito`, `::test_A19_no_queda_atascado_siguiente_ocurrencia_ejecuta` | PASS |

**Cobertura:** A01–A19 = 19/19 escenarios con al menos una prueba automatizada verde. No hay
escenarios A01–A19 sin cobertura ni ninguno en FAIL.

### Garantías transversales adicionales verificadas (relacionadas con A07/A08/A17/A19)

- **Exactamente-una-vez** ante doble tick / reintento / crash simulado e INSERT duplicado que
  viola `UNIQUE(schedule_id, due_at)`:
  `test_recurring_verification.py::test_exactamente_una_vez_doble_tick_del_scheduler`,
  `::test_exactamente_una_vez_doble_tick_reencolado_mismo_due`,
  `::test_exactamente_una_vez_insert_duplicado_viola_unique`,
  `::test_exactamente_una_vez_reintento_tras_crash_simulado` — todas PASS.
- **Reanudar sin catch-up (D06):**
  `::test_D06_reanudar_sin_catch_up_recalcula_desde_reanudacion`,
  `::test_D06_reanudar_no_ejecuta_ocurrencias_perdidas` — PASS.
- **Concurrencia de límites (T-8, conexiones distintas):**
  `test_limits.py::test_concurrencia_no_supera_limite_diario` — PASS.
- **Scheduler de fondo (único worker, arranque/parada/recuperación, sin endpoint admin):**
  8/8 en `test_scheduler.py` — PASS.

### Advertencias (no bloqueantes)

- 1 `DeprecationWarning` de `anyio.abc.BlockingPortal` (alias en `starlette.testclient`),
  dependiente de la librería, no del código de la aplicación. No afecta los resultados.

## Errores y correcciones

- Ninguno. 220/220 (suite completa) y 150/150 (archivos de aceptación C/D/E + regresión) en la
  primera ejecución. No se corrigió comportamiento ni se tocó ninguna prueba.

## Evidencia de preservación de la Etapa 1

- **DB histórica de E1 (`Etapa 1/Kiro/backend/shift_bank.db`):** SHA-256
  `407B0E132E76900FBF59412C31A2D8047A666F2BE1856BE1FF6B88531C89B4A8` — **idéntica** al hash
  registrado en las sesiones de la Fase D y de la Tarea 40; sin cambios.
- **`Etapa 2/Kiro/backend`:** no existen archivos `*.db`; las pruebas usan DB SQLite temporales
  aisladas; sin residuos.

## No modificación de código de producción

Esta sesión solo ejecutó pytest (lectura) y escribió este registro de evidencia más la marca de
la Tarea 41 en `tasks.md`. No se editó `app/`, ni las pruebas, ni el frontend, ni la Etapa 1.

## Métricas

- **Duración:** N/D (no instrumentada). pytest reportó 14,81 s (suite completa) y 10,69 s
  (archivos de aceptación verbosos).
- **Resultados:** suite completa 220/220 PASS · archivos de aceptación C/D/E + regresión 150/150
  PASS · A01–A19 19/19 cubiertos y verdes · 0 FAIL · 0 SKIP.
- **Tokens / créditos / interacciones de herramientas:** N/D (no expuestos). No se estiman.

## Alcance / restricciones respetadas

- Solo se ejecutó la Tarea 41. Las Tareas 42–46 quedan sin iniciar; las Tareas 1–40 se
  preservan intactas; total de 46 tareas intacto.
- A20 (build del frontend + suite completa registrada) y A21 (inspección manual) NO se abordan
  aquí: pertenecen a las Tareas 42 y 43.
- No se modificó código de aplicación, pruebas, requisitos, diseño, la Etapa 1 ni registros
  previos. Sin dependencias nuevas.
