# Tarea 25 — Dockerfile del backend (no root) y config de arranque

- **Fecha/hora (local):** 2026-11-17 12:54:41
- **Workspace:** `Etapa 3/Kiro`
- **Spec:** `.kiro/specs/shift-bank-stage3` · Requisitos R11.4, R12.4 · Diseño §4.1 · AC-12, AC-13
- **Decisión honrada:** D-E3-04 (Docker Compose local: backend + Nginx, red interna,
  secretos por entorno + `.env.example`, fail-closed, volumen persistente, un solo
  scheduler, no-root, SOLO verificación local). Preserva D-E3-01..04.
- **Tipo de spec:** no-bugfix (workflow feature; no hay `.config` con `specType: bugfix`).

## Archivos creados

| Archivo | Propósito |
| --- | --- |
| `Etapa 3/Kiro/backend/Dockerfile` | Imagen Python slim, runtime-only, no-root, healthcheck, DB en volumen. |
| `Etapa 3/Kiro/backend/.dockerignore` | Excluye `*.db`/WAL/SHM, `.env`, certs, `.venv`, `__pycache__`, `tests/`, `requirements-dev.txt`, `.coverage`. |
| `Etapa 3/Kiro/backend/docker-entrypoint.sh` | (Re)crea el symlink `DB_PATH → /data` en runtime y hace `exec` de uvicorn (LF, sin BOM). |

No se modificó NINGÚN código Python de la app. Por tanto el baseline de 372 pruebas
Pytest **no se ve afectado** y no se re-ejecutó (no había cambios que validar en `app/`).

## Diseño del Dockerfile

- **Base:** `python:3.12-slim`.
- **Dependencias:** instala **solo** `requirements.txt` (fastapi, uvicorn, pydantic,
  `cryptography==50.0.2`). **No** instala `requirements-dev.txt` (pytest/httpx/locust/
  coverage son dev-only, R18). Build real confirma `cryptography-50.0.2` instalado.
- **Usuario no root (R11.4, AC-13):** `appuser` UID/GID `10001`, sin home ni shell
  (`/usr/sbin/nologin`). `USER appuser` antes del `ENTRYPOINT`. `Config.User=appuser`.
- **Puerto:** `EXPOSE 8000`; uvicorn escucha `0.0.0.0:8000`. **No** se publica al host:
  en Compose solo Nginx expone 443/80 y el backend queda en la red interna (DT-9, R11.2).
- **curl:** instalado (capa mínima, `apt-get` limpiado) exclusivamente para el HEALTHCHECK.
- **Arranque:** `ENTRYPOINT docker-entrypoint.sh` + `CMD uvicorn app.main:app`. El
  `lifespan` de la app valida claves (fail-closed) y corre migraciones idempotentes
  (R12.2/R12.4) una vez que uvicorn arranca; el entrypoint NO duplica esa lógica.

## Mecanismo DB_PATH → volumen (sin cambiar código)

`config.DB_PATH` es una constante COMPUTADA:

```python
DB_PATH = Path(__file__).resolve().parent.parent / "shift_bank.db"
```

donde `__file__ = app/config.py`. Es decir, `DB_PATH = (directorio que contiene el
paquete app) / "shift_bank.db"`. En la imagen el paquete vive en `/app/app`, por lo que
`DB_PATH` resuelve a **`/app/shift_bank.db`**.

No se puede montar el volumen directamente en `/app` porque sombrearía el código. El
diseño §4.1 pide "montar el volumen en la ruta de `DB_PATH`". Mecanismo elegido
(preferido en el enunciado: montaje-en-la-ruta, sin tocar código):

1. Directorio de datos dedicado **`/data`**, respaldado por el **volumen Docker nombrado**
   (`VOLUME ["/data"]`; wiring del nombre del volumen en Compose, Tarea 27).
2. **Symlink `/app/shift_bank.db` → `/data/shift_bank.db`**, creado por el entrypoint en
   runtime (idempotente), porque el volumen se monta al iniciar el contenedor (post-build).
3. SQLite sigue el symlink: la DB y sus sidecars WAL/SHM viven en el volumen persistente;
   el código permanece intacto. `/data` es propiedad de `appuser:10001` en la imagen, así
   que un volumen nombrado vacío hereda ese ownership y el usuario no root puede escribir.

**Por qué este mecanismo:** honra §4.1 (el volumen respalda exactamente la ruta que
`DB_PATH` resuelve) sin modificar `config.py` (no se introduce una variable de entorno
nueva), preservando el fail-closed y las 372 pruebas. Evita el conflicto de sombreado de
código que tendría un montaje directo en `/app`.

## Healthcheck

La app **no** expone un endpoint `/health` dedicado (verificado en `main.py` y en todos
los routers). Se usa un GET existente y liviano: **`GET /api/accounts`**, la misma ruta
que el runner de carga (`loadtest`) emplea como sonda de salud. No se inventó un endpoint
nuevo. `HEALTHCHECK`: `curl -fsS http://127.0.0.1:${APP_PORT}/api/accounts`, interval 15s,
timeout 5s, start-period 20s, retries 5. Si el arranque falla-cerrado, uvicorn no sirve y
el healthcheck queda `unhealthy` (R12.2).

## Verificación REALIZADA (Docker daemon disponible: Docker 29.9.3)

| Check | Resultado | Evidencia |
| --- | --- | --- |
| `docker build` | **PASS (real)** | Imagen `shift-bank-backend:task25` (243 MB) construida; `Successfully installed ... cryptography-50.0.2 ...`. |
| Usuario por defecto no root | **PASS (real)** | `docker run --rm img id` → `uid=10001(appuser)`; `Config.User=appuser`. |
| HEALTHCHECK definido | **PASS (real)** | `image inspect .Config.Healthcheck` → `CMD-SHELL curl -fsS .../api/accounts`, interval 15s/timeout 5s/start 20s/retries 5. |
| Fail-closed sin claves | **PASS (real)** | `docker run` sin `SHIFT_*` → `ConfigError: SHIFT_ENC_KEYS ausente...` → `Application startup failed. Exiting.` (exit 3). |
| Arranque OK con claves de prueba | **PASS (real)** | volumen desechable `sb_task25_data`; contenedor `healthy`; `GET /api/accounts` → cuentas sembradas. |
| DB en el volumen vía symlink | **PASS (real)** | `/app/shift_bank.db -> /data/shift_bank.db`; `/data/shift_bank.db` (110592 bytes) creado por `appuser` sobre el volumen. |
| runtime no root | **PASS (real)** | `docker exec id -u` → `10001`. |

Teardown: contenedor y volumen desechables (`sb_ok`, `sb_task25_data`) y la imagen de
prueba fueron eliminados tras verificar; no quedan residuos. Se usaron **volúmenes
desechables aislados**; no se tocaron datos reales (R13.6).

## DIFERIDO a la Tarea 28 (smoke de despliegue completo)

- Build + `up` del **stack completo** (backend + Nginx) con `docker compose`, HTTPS,
  redirección HTTP→HTTPS, proxy `/api`, y supervivencia de cifrado/auditoría tras
  reinicio. El wiring de `.env`/secretos y del nombre del volumen es de la Tarea 27; el
  smoke integral de despliegue es la Tarea 28. Aquí solo se verificó la imagen del backend
  de forma aislada.

## Notas de cumplimiento

- Sin secretos ni DB horneados en la imagen (R2.1, R12.5): `.dockerignore` excluye `*.db`
  (+ WAL/SHM/journal), `.env*` (salvo `.env.example`), `*.pem/*.key/*.crt/*.p12/*.pfx`,
  `certs/`. Los `SHIFT_*` se inyectan por entorno en runtime (Tarea 27).
- No se usó hosting externo, Kubernetes ni CI/CD (R11.5). Verificación 100% local.
