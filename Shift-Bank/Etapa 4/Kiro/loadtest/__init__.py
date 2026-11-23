"""Arnés de pruebas de carga de Shift Bank (Etapa 3, D-E3-03 → R9, R10).

Este paquete es **tooling de pruebas/carga**, no runtime de la aplicación. Agrupa los
bloques de construcción de la prueba de carga Locust:

- `isolation` (Tarea 18): aislamiento de una DB SQLite sintética desechable + claves de
  prueba fijadas por entorno **antes de importar la app** (R10.1), con siembra determinista
  de saldos/límites amplios (R10.2).
- `locustfile` (Tarea 19): `HttpUser` con la mezcla 60/30/10 (`@task` 6/3/1) y controles
  bancarios preservados (montos pequeños bajo el umbral MFA, dirección alternada), con
  clasificación de rechazos de negocio esperados (4xx) frente a errores inesperados (5xx/
  transporte) vía `catch_response=True` (R9.2, R10.3).
- `run_loadtest` (Tarea 20): runner que aísla+siembra la DB sintética ANTES de arrancar la
  app, lanza uvicorn (vía `_uvicorn_launcher`, que parchea `DB_PATH` en el proceso hijo) sobre
  esa DB, espera salud con timeout acotado y ejecuta Locust HEADLESS con la configuración exacta
  (30 usuarios / 5 por segundo / 60 s de steady-state tras el ramp-up de 6 s). Falla ruidosamente
  (salida != 0) si el servicio no queda disponible; nunca reporta un servicio caído como válido
  (R9.1). Teardown limpio de Locust, uvicorn y la DB sintética.
- `_uvicorn_launcher` (Tarea 20): bootstrap del subproceso uvicorn; parchea
  `config.DB_PATH`/`db.DB_PATH` desde el entorno ANTES de importar `app.main` (la app NO lee
  `DB_PATH` del entorno por sí sola), garantizando el aislamiento (R10.1).
- `verify_invariants` (Tarea 22): se añade en una tarea posterior.

Nunca toca la base de datos histórica ni `SEED-3.md`.
"""
