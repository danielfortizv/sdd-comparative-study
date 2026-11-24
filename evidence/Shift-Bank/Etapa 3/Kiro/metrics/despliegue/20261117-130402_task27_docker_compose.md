# Tarea 27 — `docker-compose.yml`: red interna, volumen, secretos y un solo scheduler

- **Timestamp:** 2026-11-17 13:04:02 (-05:00)
- **Workspace:** `Etapa 3/Kiro`
- **Decisión:** D-E3-04 (backend + Nginx, red interna, secretos por entorno + `.env.example`,
  fail-closed, volumen persistente, UN SOLO scheduler, no root, SOLO verificación local).
- **Requisitos:** R11.3, R11.5, R12.1, R12.3, R12.5, R17.3 · **Diseño:** §4.1, §4.3 · **AC:** AC-12, AC-13
- **Entorno:** Docker Engine 29.9.3, Docker Compose v5.7.0, Windows.

## Archivos creados / modificados

| Archivo | Acción | Propósito |
|---------|--------|-----------|
| `Etapa 3/Kiro/docker-compose.yml` | NUEVO | Topología de 2 servicios (backend + nginx), red interna, volumen, secretos por entorno, 1 réplica. |
| `Etapa 3/Kiro/.env.example` | NUEVO | Plantilla versionada con los NOMBRES de las 4 variables `SHIFT_*` (sin secretos). |
| `Etapa 3/Kiro/.gitignore` | NUEVO (raíz) | Excluye `*.db`, `.env` (conserva `.env.example`), `certs/` y material TLS. |

### Ubicación del compose
Colocado en la **raíz del workspace Kiro** (no en `deploy/` como sugería el diseño §4.1): los
Dockerfiles ya viven en `backend/` y `frontend/`, y Nginx referencia el upstream `backend` por
nombre de servicio. La raíz permite contextos de build directos (`./backend`, `./frontend`) sin
mover ni duplicar artefactos.

### `.dockerignore` raíz
NO se añadió. Ningún contexto de build usa la raíz del workspace; los contextos son `./backend` y
`./frontend`, cada uno con su propio `.dockerignore` (Tareas 25/26) que ya excluye `*.db`, `.env`
y certs. Un `.dockerignore` en la raíz no tendría efecto. Los `.gitignore` por carpeta se
preservan intactos; el nuevo `.gitignore` raíz los complementa (no reemplaza reglas existentes).

## Topología de Compose

```
[host] --443/80--> (nginx)  --red interna "shiftnet" (internal:true)-->  (backend:8000)
                     |                                                        |
            único con ports:                                       SIN ports: al host
            443 HTTPS, 80 redirect                                 volumen shift_db_data -> /data
```

- **Servicios (exactamente dos):** `backend` y `nginx`.
- **backend:** `build ./backend/Dockerfile`; **NO** tiene bloque `ports:` → inalcanzable desde el
  host (R11.2). Solo en la red `shiftnet`. Secretos por `env_file: .env` + `environment:` con
  `${VAR}` (sin default). Volumen `shift_db_data:/data` (respalda `DB_PATH`). Healthcheck
  reafirmado (GET /api/accounts; ya horneado en la imagen). `restart: unless-stopped`.
- **nginx:** `build ./frontend/Dockerfile`; **único** con `ports: 443:443` y `80:80` (R11.1).
  Monta certs de solo lectura `./certs:/etc/nginx/certs:ro` (provisionados externamente, NO
  horneados, R4.4). `depends_on: backend condition: service_healthy`.
- **Red `shiftnet`:** `driver: bridge`, `internal: true` → sin gateway al host ni salida a
  Internet para los contenedores; el backend solo es alcanzable por nginx en la misma red
  (R4.3, R11.2). Los puertos publicados de nginx son NAT del host gestionado por Compose y NO
  requieren salida de la red, por lo que `internal: true` es compatible con exponer 443/80. Las
  imágenes se CONSTRUYEN localmente (`build:`), no se descargan por esta red, así que `internal`
  no impide el arranque (R11.5).
- **Volumen `shift_db_data`:** `driver: local`, nombrado y persistente; el archivo SQLite
  (incl. `audit_log`/`audit_anchor` y sidecars WAL/SHM) sobrevive reinicios (R12.3, R13.4).

## Un solo scheduler (R11.3, R17.3)
El servicio `backend` corre como UNA SOLA instancia. **No** se define `deploy.replicas` (>1
rompería la garantía) ni se usa `--scale backend=N`. El `lifespan` heredado lanza exactamente un
scheduler de fondo por proceso; con un único contenedor hay exactamente un scheduler. Escalar el
backend queda fuera de alcance (violaría la exactitud-una-vez de recurrencias/settlement ACH).

## Secretos por entorno (R12.1, §4.3)
El compose NO contiene literales de secretos. Las 4 variables requeridas
(`SHIFT_ENC_KEYS`, `SHIFT_ENC_ACTIVE_KID`, `SHIFT_AUDIT_HMAC_KEY`, `SHIFT_ADMIN_TOKEN`) se
inyectan desde `.env` (NO versionado). Fail-closed: sin `.env`/claves, el backend aborta en
`lifespan`, el healthcheck nunca pasa y nginx no arranca su dependencia (R12.2).

### `.env.example` (solo nombres, sin valores reales)
Documenta los 4 nombres con valores en blanco y comentarios para generar claves reales:
`SHIFT_ENC_KEYS` (mapa `kid:base64` de 32 bytes AES-256), `SHIFT_ENC_ACTIVE_KID` (kid activo),
`SHIFT_AUDIT_HMAC_KEY` (base64 aleatorio), `SHIFT_ADMIN_TOKEN` (token admin). Sin secretos.

### Reglas de ignore
- `.gitignore` raíz: `*.db`, `*.db-wal/-shm/-journal`, `.env`, `.env.*`, `!.env.example`,
  `certs/`, `*.pem/*.key/*.crt/*.p12/*.pfx`.
- Verificado con `git check-ignore -v`: `Etapa 3/Kiro/.env` → ignorado (regla `.env`);
  `Etapa 3/Kiro/.env.example` → NO ignorado (negación `!.env.example`).

## Verificación REAL `docker compose config`

**Comando** (con `.env` DESECHABLE de solo-pruebas, valores tipo conftest, luego ELIMINADO):

```
docker compose config   # cwd: Etapa 3/Kiro
```

**Resultado REAL: exit 0** (parsea y valida). Resumen del render:
- `services:` exactamente `backend` y `nginx`.
- `backend`: SIN clave `ports:` (ningún mapeo al host) → **una sola instancia, sin host ports**.
- `backend.environment`: las 4 `SHIFT_*` provienen de interpolación del entorno (no literales en
  el YAML fuente; el render muestra los valores de prueba inyectados desde el `.env` desechable).
- `backend.volumes`: `shift_db_data -> /data` (type volume).
- `backend.build.context`: `.../Kiro/backend` (sin DB ni secretos horneados; .dockerignore lo
  garantiza).
- `nginx.ports`: `443:443` y `80:80` (ingress tcp); `nginx.volumes`: bind `./certs ->
  /etc/nginx/certs` read_only; `depends_on.backend.condition: service_healthy`.
- `networks.shiftnet`: `driver: bridge`, `internal: true`.
- `volumes.shift_db_data`: `driver: local`.
- **Sin réplicas** (`deploy.replicas` ausente) → exactamente un backend / un scheduler.
- **Sin secretos ni DB horneados** en imágenes (contextos de build con `.dockerignore`).

**Fail-closed confirmado:** tras ELIMINAR el `.env` desechable, `Test-Path .env` → `False` y
`docker compose config` **falla (exit 1)**: advierte que las 4 `SHIFT_*` no están definidas y que
`.env` no existe. Esto prueba que el stack depende enteramente de secretos externos (no horneados).

### `.env` desechable
Creado solo para validar el render; contenía valores de PRUEBA (no reales, estilo conftest:
`SHIFT_ENC_KEYS=test:...`). **ELIMINADO** tras la verificación y confirmado ausente. Estaba
git-ignorado en todo momento; no se versionó ningún secreto real ni de prueba.

## Confirmaciones clave
- ✅ Exactamente DOS servicios (backend, nginx).
- ✅ backend SIN puertos al host; nginx expone 443/80 (único expuesto).
- ✅ Red interna aislada `shiftnet` (`internal: true`).
- ✅ Volumen nombrado persistente `shift_db_data` para `DB_PATH`.
- ✅ Exactamente UNA réplica de backend → UN scheduler (sin `deploy.replicas`).
- ✅ Secretos por entorno (`.env` no versionado); `.env.example` versionado sin secretos.
- ✅ Ignore de `*.db`, `.env` (conserva `.env.example`), certs.
- ✅ `docker compose config` válido (exit 0); fail-closed sin `.env` (exit 1).

## Diferido a Tareas 28/29 (NO ejecutado aquí)
- **T28:** build + `docker compose up` con healthchecks saludables; smoke de HTTPS, redirección
  HTTP→HTTPS, proxy `/api`, llamada representativa sobre TLS (volúmenes desechables).
- **T29:** operación bancaria + MFA + beneficiario (token `enc:` en DB del volumen) +
  `verify_chain`; negativo fail-closed (quitar una clave); persistencia tras reinicio.
- La generación de los certs de prueba en `./certs` (server.crt/server.key) también es parte del
  smoke de despliegue (T28/T29), no de T27.
