# E2 · Kiro · Sesión de implementación 09 — Tarea 9

- **Fecha:** 2026-11-16
- **Tarea:** 9 — Abstracción de reloj inyectable (`clock.py`)
- **Objetivo:** proveer manejo de tiempo UTC determinista y testable para la funcionalidad
  futura de la Etapa 2 (settlement ACH, recurrentes), sin implementar scheduler ni cambiar el
  comportamiento MFA heredado.
- **Estado final:** COMPLETED

## Mecanismos de tiempo heredados inspeccionados

- `app/service.py`: `_now_utc()` = `datetime.now(timezone.utc)`; `_iso()` usa el formato
  `%Y-%m-%dT%H:%M:%SZ`; `_parse_iso()` lo invierte; la expiración MFA es perezosa y compara
  `_now_utc()` contra `expires_at` persistido (ventana 5 min).
- Las pruebas de MFA (Tarea 4) monkeypatchean `app.service._now_utc`.

## Abstracción de reloj implementada (`app/clock.py`)

- `Clock` (Protocol): `now_utc() -> datetime` (UTC timezone-aware).
- `SystemClock`: reloj real del sistema (producción).
- `ManualClock`: reloj controlado para tests — `now_utc()`, `advance(seconds/minutes/hours/
  days)`, `set(moment)`. Sin estado global mutable (cada instancia es local); lecturas
  repetidas no avanzan el tiempo.
- `system_clock`: instancia por defecto (SystemClock) para producción.
- Helpers compatibles con la persistencia heredada: `ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"`,
  `iso(dt)`, `parse_iso(text)`, `utc_day_bounds(moment)` (para la futura agregación diaria de
  límites, día UTC). `_ensure_utc` normaliza naive→UTC.

Sin librerías externas de mocking ni dependencias nuevas; sin temporizadores reales.

## Decisiones de diseño e integración

- **Compatibilidad MFA (preservada):** NO se modificó `app/service.py` ni `_now_utc`. La
  abstracción de reloj es una **utilidad compartida nueva e independiente**; refactorizar
  `service._now_utc` para usarla habría cambiado el contrato que las pruebas de la Tarea 4
  monkeypatchean, y pertenece a otras tareas. El comportamiento MFA, su semántica de expiración
  y su testabilidad por monkeypatch quedan intactos. No se requirió adaptador de compatibilidad.
- **Formato de persistencia:** `clock.iso`/`clock.parse_iso` replican exactamente el formato
  heredado (`...Z`), de modo que los timestamps que generen ACH/recurrentes sean interoperables
  con los de `service`.
- **Inyección en tests:** las futuras operaciones de settlement/recurrentes recibirán un `Clock`
  por parámetro; los tests pasarán un `ManualClock` y avanzarán el tiempo con `advance(...)`,
  sin `sleep()`. Demostrado en `test_control_de_tiempo_sin_sleep`.

## Estado del repositorio

- **Commit (HEAD):** `da4209dc3ea9eda08f13de08abe29800bcdf6513` (sin commit nuevo).
- **Etapa 1 (`Etapa 1/Kiro`):** git limpio antes y después.
- **Código de aplicación en esta tarea:** `backend/app/clock.py` (NUEVO). No se modificó
  `service.py` ni ningún otro módulo heredado.

## Hash de la base de datos histórica

- **Antes y después:** `407B0E132E76900FBF59412C31A2D8047A666F2BE1856BE1FF6B88531C89B4A8` —
  sin cambios.

## Archivos creados / modificados

| Acción | Archivo |
|---|---|
| Creado | `Etapa 2/Kiro/backend/app/clock.py` |
| Creado | `Etapa 2/Kiro/backend/tests/test_clock.py` (10 pruebas) |
| Modificado | `Etapa 2/Kiro/.kiro/specs/shift-bank-stage2/tasks.md` (marcada solo la Tarea 9) |
| Creado | `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_09_TAREA_09.md` (este registro) |

## Pruebas añadidas (10) y resultados

- reloj del sistema devuelve UTC válido; ManualClock devuelve el instante fijado; avance
  determinista; lecturas repetidas no avanzan; `set` fija instante; fronteras de día UTC;
  formato/parseo compatibles con persistencia heredada; `iso` normaliza naive; control de tiempo
  sin `sleep`; `system_clock` por defecto.
- `python -m pytest tests/test_clock.py -v` → **10 passed in 0.06s** (exit 0).

## Verificación de regresión

- MFA (Tarea 4): `python -m pytest tests/test_regression_mfa.py -q` → **14 passed** (intactas).
- Suite completa: `python -m pytest` → **79 passed, 101 warnings in 3.95s** (exit 0):
  51 (Fase A) + 6 (migración T7) + 12 (esquema T8) + 10 (reloj T9). **Passed 79 · Failed 0 ·
  Skipped 0.**
- No se debilitó, eliminó ni modificó ninguna aserción de regresión.

## Verificación de integridad de la BD

- DB histórica: SHA-256 idéntico antes/después. `shift_bank.db` no existe en `Etapa 2/Kiro/
  backend`; sin DB temporales residuales. `Etapa 1/Kiro` git limpio.

## Errores y correcciones

- Ninguno. Las 10 pruebas del reloj y las 79 de la suite pasaron en la primera ejecución.

## Métricas

- **Duración de la sesión:** N/D. pytest: 0,06 s (T9) y 3,95 s (suite).
- **Tokens / créditos / interacciones de herramientas:** N/D (no expuestos). No se estiman.

## Alcance / restricciones respetadas

- Solo se ejecutó la Tarea 9. Tareas 10–46 sin iniciar y sin marcar; Tareas 1–8 preservadas.
- No se implementaron utilidades financieras (Tarea 10), límites por defecto, settlement ACH,
  recurrentes ni scheduler; no se cambió el esquema de BD de las Tareas 7–8; no se tocó el
  frontend, contratos de API, requisitos/diseño, la Etapa 1 ni registros previos; sin
  dependencias nuevas; sin estado global mutable ni librerías de mocking.
