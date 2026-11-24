# E2 · Kiro · Sesión de implementación 04 — Tarea 4

- **Fecha:** 2026-11-16
- **Tarea:** 4 — (verificación) Pruebas de regresión: MFA heredada
- **Objetivo:** fijar el comportamiento heredado del MFA simulado en transferencias internas
  (umbral, PENDING_MFA sin mover saldos, confirmación correcta/incorrecta, expiración a 5 min,
  re-verificación de fondos, idempotencia), con control de tiempo determinista.
- **Estado final:** COMPLETED

## Estado del repositorio

- **Commit:** `ebf1017748928b30a9a5ad68a56b9b532f304e86` (sin commit nuevo).
- **Etapa 1 (`Etapa 1/Kiro`):** git limpio, sin cambios.
- **DB histórica E1 (`shift_bank.db`):** 36 864 bytes, 13/10/2026 2:58:26 p. m. — sin modificar.

## Comportamiento MFA heredado observado (fuente de los asertos)

- `config.py`: `MFA_THRESHOLD = 1000000`, `MFA_CODE = "123456"`, `MFA_TTL_SECONDS = 300` (5 min).
- `service.create_transfer`: `requires_mfa = amount >= 1000000`; si aplica → crea `PENDING_MFA`
  con `expires_at = now+5min`, `reference = uuid4().hex`, **sin tocar saldos**.
- `service.confirm_mfa`: expiración perezosa (`_now_utc()` vs `expires_at`) → `EXPIRED`;
  estado ≠ PENDING_MFA → DomainError `EXPIRED`; código incorrecto → `INVALID_MFA_CODE`, sigue
  PENDING_MFA (sin lockout); correcto + fondos insuficientes → `FAILED`; correcto + fondos →
  `apply_transfer` → `COMPLETED`.
- `routers/transfers.py`: `INVALID_MFA_CODE` 401, `EXPIRED` 409, `INSUFFICIENT_FUNDS` (confirmar)
  409, `NOT_FOUND` 404; creación 201.

No se modificó código de aplicación; las pruebas verifican el contrato tal cual.

## Archivos creados / modificados

| Acción | Archivo |
|---|---|
| Creado | `Etapa 2/Kiro/backend/tests/test_regression_mfa.py` (14 pruebas) |
| Modificado | `Etapa 2/Kiro/.kiro/specs/shift-bank-stage2/tasks.md` (marcada solo la Tarea 4) |

Sin cambios en código de aplicación, configuración MFA, requisitos, diseño, Etapa 1 ni
registros previos.

## Casos de prueba introducidos (14)

**A. Umbral:** <1.000.000 no requiere MFA; ==1.000.000 requiere; >umbral requiere; respuesta
inicial con `{status, mfa_required, reference, expires_at}`.

**B. Pendiente:** PENDING_MFA no debita ni acredita; pendiente visible en historial con estado
`PENDING_MFA`.

**C. Confirmación correcta:** código `123456` → `COMPLETED` (200), débito+crédito, total
preservado; historial conserva forma heredada y estado MAYÚSCULAS.

**D. Confirmación inválida:** código incorrecto → 401 `INVALID_MFA_CODE`, sigue PENDING_MFA,
**sin lockout** (3 intentos y luego el correcto AÚN completa), sin débito; referencia
inexistente → 404 `NOT_FOUND`.

**E. Expiración:** tras >5 min (reloj avanzado) → 409 `EXPIRED` sin débito; una EXPIRED no
completa ni con código correcto.

**F. Re-verificación e idempotencia:** fondos insuficientes al confirmar → 409
`INSUFFICIENT_FUNDS`; confirmación repetida tras COMPLETED no debita/acredita dos veces (segundo
intento ≠ 200, saldos sin cambio adicional).

## Estrategia de control de tiempo determinista

Para la expiración se **monkeypatcheó `app.service._now_utc`** (solo en el entorno de test) para
devolver `now + 301s` / `+600s`, forzando que la expiración perezosa evalúe la ventana como
vencida sin esperar 5 minutos reales. No se modificó código de producción. Para "fondos
insuficientes al confirmar" se manipuló el saldo **solo en la DB aislada del test** (no en
código de aplicación), simulando una caída de fondos entre creación y confirmación.

## Comandos ejecutados y resultados reales

1. `python -m pytest tests/test_regression_mfa.py -v` → **14 passed, 31 warnings in 1.32s**
   (exit 0).
2. `python -m pytest -q` (suite completa) → **38 passed, 75 warnings in 2.52s** (exit 0):
   4 (T1) + 8 (T2) + 12 (T3) + 14 (T4). Tareas 1–3 siguen pasando.

- Passed: **38** · Failed: **0** · Skipped: **0** · Warnings: 75 (deprecation, no bloqueantes).

### Advertencias (no bloqueantes)

- `DeprecationWarning: on_event is deprecated` (patrón heredado de E1; migración en Tarea 12) y
  alias de anyio en `TestClient`.

## Hallazgos de consistencia financiera e idempotencia

- PENDING_MFA no mueve saldos; el movimiento ocurre solo al pasar a COMPLETED.
- Confirmación repetida: el estado terminal tras COMPLETED impide un segundo débito (la segunda
  llamada responde 409, saldos invariables). El mecanismo heredado protege contra doble efecto en
  la ruta MFA interna.
- Código incorrecto no marca FAILED ni bloquea: coincide con el comportamiento real inspeccionado
  (sin lockout). No se asumió transición a FAILED por intento inválido.

## Inconsistencias del baseline / correcciones

- Ninguna. 14/14 en la primera ejecución; comportamiento observado = contrato heredado. No se
  reparó comportamiento de la Etapa 1. (Corrección menor en el propio test: se eliminó una
  expresión redundante antes de ejecutar; no afectó al código de aplicación.)

## Evidencia de aislamiento y preservación de la Etapa 1

- `shift_bank.db` no existe en `Etapa 2/Kiro/backend` (solo DB temporales); sin residuos.
- DB histórica de E1 sin cambios (tamaño/fecha idénticos). `Etapa 1/Kiro` git limpio.

## Métricas

- **Duración:** no instrumentada; pytest reportó 1,32 s (T4) y 2,52 s (suite).
- **Tokens / créditos / interacciones de herramientas:** no disponibles (no expuestos). No se
  estiman.

## Alcance / restricciones respetadas

- Solo se ejecutó la Tarea 4. Tareas 5–46 sin iniciar y sin marcar; Tareas 1–3 preservadas.
- No se cambió la configuración/reglas de MFA, ni lógica de negocio, ni contratos de API; no se
  implementó ACH/recurrentes/límites; no se tocó la Etapa 1 ni registros previos; sin
  dependencias nuevas. No se reclama cobertura de los flujos de autorización de la Etapa 2.
