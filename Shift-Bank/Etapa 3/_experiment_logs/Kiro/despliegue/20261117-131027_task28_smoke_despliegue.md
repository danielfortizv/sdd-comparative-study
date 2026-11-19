# Tarea 28 (auto)(verificación) — Smoke de despliegue: build/up/health/HTTPS/redirect/proxy

- **Fecha/hora**: 2026-11-17 13:10 (local) · 18:07–18:10 UTC
- **Workspace**: `Etapa 3\Kiro`
- **Spec**: `.kiro/specs/shift-bank-stage3` · **Requisitos**: R13.1, R13.2 · **Diseño**: §4.4 · **AC**: AC-12
- **Entorno real**: Docker Engine **29.9.3**, Docker Compose **v5.7.0**, OpenSSL **3.3.0** (host Windows/PowerShell)
- **Proyecto Compose aislado**: `-p shiftsmoke` (contenedores/volumen/red con prefijo `shiftsmoke_`, 100% desechables)

> **VEREDICTO GLOBAL: FAIL** — `config`, `build`, `up` y `healthchecks` PASAN de verdad, pero el
> smoke orientado al host (HTTPS / redirección / proxy `/api` / llamada TLS representativa) **NO
> es alcanzable con el `docker-compose.yml` de la Tarea 27 tal como está**: devuelve `000`
> (conexión rechazada). Causa raíz probada abajo. El smoke solo PASA tras corregir la topología
> (nginx necesita además una red **no interna**). Según la regla dura "un curl fallido es FAIL",
> no se marca PASS. La corrección es un defecto de la Tarea 27 (topología), no de esta verificación.

---

## 0. Preparación desechable (test-only, git-ignored, borrado al final)

### 0.1 Certificado TLS autofirmado de usar y tirar (`certs/server.crt` + `server.key`)
El OpenSSL del host tenía un `openssl.cnf` roto (`Z:/extlib/.../openssl.cnf` inexistente), por lo
que se apunta `OPENSSL_CONF` a un archivo temporal vacío. Comando exacto (PowerShell):

```powershell
$cfg = New-TemporaryFile; $env:OPENSSL_CONF = $cfg.FullName
openssl req -x509 -newkey rsa:2048 -nodes `
  -keyout .\certs\server.key -out .\certs\server.crt `
  -days 2 -subj "/CN=localhost" `
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
Remove-Item $cfg.FullName -Force; Remove-Item Env:\OPENSSL_CONF
```

Verificación del cert generado (`openssl x509 -noout -subject -issuer -dates -ext subjectAltName`):
```
subject=CN=localhost
issuer=CN=localhost
notBefore=Nov 17 18:07:16 2026 GMT
notAfter =Nov 19 18:07:16 2026 GMT   (2 días)
X509v3 Subject Alternative Name: DNS:localhost, IP Address:127.0.0.1
```
Al ser autofirmado se usa `curl -k` en todo el smoke HTTPS (verificación de cadena deshabilitada
a propósito; es un cert de prueba, no una CA confiable).

### 0.2 `.env` de usar y tirar (secretos de prueba, estilo conftest)
```
SHIFT_ENC_KEYS=test:c2hpZnQtYmFuay1zdGFnZTMtdGVzdC1rZXktMzJieXQ=
SHIFT_ENC_ACTIVE_KID=test
SHIFT_AUDIT_HMAC_KEY=dGVzdC1hdWRpdC1obWFjLWtleS1zdGFnZTMtc21va2U=
SHIFT_ADMIN_TOKEN=test-admin-token-stage3-smoke
```
Validaciones previas:
- `SHIFT_ENC_KEYS` decodifica base64 a **exactamente 32 bytes** (requisito fail-closed). ✓
- `git check-ignore .env certs/server.crt certs/server.key` → los tres **ignorados** por git. ✓

---

## 1. `docker compose config` → **PASS**
```
docker compose -p shiftsmoke config   →  exit 0
```
- Secretos interpolados desde `.env` (4 variables presentes).
- `backend` **sin** bloque `ports` (no publicado al host).
- `nginx` publica `443:443` y `80:80`; monta `./certs:/etc/nginx/certs:ro`; `depends_on backend
  condition: service_healthy`.
- Red `shiftsmoke_shiftnet` con `internal: true`; volumen nombrado `shiftsmoke_shift_db_data`.

## 2. `docker compose build` → **PASS**
```
docker compose -p shiftsmoke build    →  exit 0
```
Ambas imágenes construidas de verdad: `shift-bank-backend:stage3` y `shift-bank-frontend:stage3`
(capas cacheadas de T25/T26, re-exportadas OK). Sin DB ni secretos horneados (`.dockerignore`).

## 3. `docker compose up -d` → **PASS (arranque)**
```
docker compose -p shiftsmoke up -d    →  exit 0
```
Secuencia real: `backend Started → Waiting → Healthy`, luego `nginx Started` (respeta
`depends_on service_healthy`).

## 4. Healthchecks → **PASS**
```
docker compose -p shiftsmoke ps
SERVICE   STATUS                    PORTS
backend   Up 12 seconds (healthy)   8000/tcp        <- 8000 es puerto INTERNO, no publicado
nginx     Up 6 seconds (healthy)    80/tcp, 443/tcp

docker inspect .State.Health.Status
shiftsmoke-backend-1: running / health=healthy
shiftsmoke-nginx-1  : running / health=healthy
```

---

## 5. Smoke orientado al host — **FAIL con el compose tal cual**

### 5.1 Resultados reales (stack de la Tarea 27, sin modificar)
```
1) curl -k https://localhost/                  → http_code=000           (sin respuesta)
2) curl http://localhost/  (redirect)          → http_code=000 redirect_url=(vacío)
3) curl -k https://localhost/api/accounts      → http_code=000
4) curl http://localhost:8000/api/accounts     → http_code=000, curl_exit=7
```
Todo `000`, incluido el 443/80 de nginx que debería responder. **No es un fallo de backend: es
que los puertos publicados de nginx NO están enlazados al host.**

### 5.2 Causa raíz (probada)
```
docker port shiftsmoke-nginx-1                 → (vacío)
docker inspect .NetworkSettings.Ports          → {"443/tcp":[],"80/tcp":[]}   <- sin binding host
docker inspect redes de nginx                  → shiftsmoke_shiftnet (ÚNICA)
docker network inspect shiftsmoke_shiftnet     → internal=true
docker logs nginx                              → healthcheck interno Wget GET / → 200 (nginx vivo)
```
nginx está en **una sola** red, `shiftnet`, que es `internal: true`. En este motor Docker, un
contenedor cuya **única** red es interna **no puede** tener sus puertos publicados enlazados al
host (no hay ruta de NAT host ↔ red interna). El comentario del `docker-compose.yml` (T27) que
afirma que "los puertos publicados son NAT del host y no dependen de que la red tenga salida" es
**incorrecto en la práctica** para este caso. nginx funciona (su propio healthcheck da 200), pero
es inalcanzable desde el host.

### 5.3 Confirmación de la causa raíz + evidencia real de smoke (override desechable)
Override temporal (`docker-compose.smoke-override.yml`, NO versionado, borrado al final) que añade
una segunda red **no interna** `edge` **solo a nginx** (backend sigue aislado en `shiftnet`):
```yaml
services:
  nginx:
    networks: [shiftnet, edge]
networks:
  edge: { driver: bridge, internal: false }
```
```
docker compose -p shiftsmoke -f docker-compose.yml -f docker-compose.smoke-override.yml up -d
docker port shiftsmoke-nginx-1
  80/tcp  -> 0.0.0.0:80   / [::]:80
  443/tcp -> 0.0.0.0:443  / [::]:443        <- AHORA sí enlazados al host
```
Smoke real con la topología corregida (ambos servicios `healthy`):
```
1) HTTPS SPA        curl -k https://localhost/
   → http_code=200 content_type=text/html                              PASS
2) HTTP->HTTPS      curl http://localhost/
   → http_code=301 redirect_url=https://localhost/                     PASS
   (headers crudos: HTTP/1.1 301 Moved Permanently; Server: nginx/1.27.5;
    Location: https://localhost/)
3) /api sobre TLS   curl -k https://localhost/api/accounts
   → http_code=200 content_type=application/json                       PASS
   body: {"accounts":[{"name":"Checking","balance":"5000000.00"},
                      {"name":"Savings","balance":"15000000.00"}]}      (seed real proxied)
4) backend NO expuesto  curl http://localhost:8000/api/accounts
   → http_code=000, curl_exit=7 (conexión rechazada)                   PASS (correcto: aislado)
```
Esto prueba de forma concluyente que (a) el defecto está en la topología de red de nginx, y
(b) con una red no interna añadida a nginx todos los checks de R13.2 pasan de verdad, con el
backend aún inalcanzable desde el host (R11.2/AC-12 preservado).

---

## 6. Veredictos por check

| Check | Requisito | Resultado (compose T27 tal cual) |
|-------|-----------|----------------------------------|
| `docker compose config` | R13.1 | **PASS** (exit 0) |
| `docker compose build`  | R13.1 | **PASS** (exit 0, ambas imágenes) |
| `docker compose up -d`  | R13.1 | **PASS** (exit 0) |
| Healthchecks (backend+nginx `healthy`) | R13.1 | **PASS** |
| HTTPS (`curl -k https://localhost/`) | R13.2 | **FAIL** → `000` (nginx no enlaza puertos) |
| Redirección HTTP→HTTPS | R13.2 | **FAIL** → `000` |
| Proxy `/api` sobre TLS (llamada representativa) | R13.2 | **FAIL** → `000` |
| Backend NO expuesto en host:8000 | R11.2/AC-12 | PASS (rechazado, exit 7) |

**Con el override correctivo** (nginx + red no interna): HTTPS **200**, redirect **301→https**,
`/api` **200 JSON seed real**, backend aún inalcanzable → los checks de R13.2 pasan de verdad.

**GLOBAL: FAIL** contra el artefacto entregado. La topología de la Tarea 27 debe corregirse
(añadir a nginx una red no interna, manteniendo el backend en la red `internal: true`) para que
R13.2 pase sin override.

---

## 7. Teardown y limpieza (confirmado)
```
docker compose -p shiftsmoke -f docker-compose.yml -f docker-compose.smoke-override.yml down -v
  → exit 0; contenedores, volumen shiftsmoke_shift_db_data, redes shiftnet y edge REMOVIDOS
docker ps -a  / volume ls / network ls  (filtro shiftsmoke)  → (vacío en los tres)
```
Borrado de artefactos desechables:
```
env_absent=True        (.env borrado)
certs_absent=True      (certs/ borrado)
override_absent=True   (docker-compose.smoke-override.yml borrado)
raíz workspace: .kiro, backend, frontend, loadtest, .env.example, .gitignore, docker-compose.yml
```
Datos históricos intactos:
```
backend/shift_bank.db  SHA256 = 33E74D26F33D13449AA658171D50CFF65453FEFC57E20373D118E534243353CC
  (idéntico antes y después; el stack usó el volumen Docker desechable, nunca este archivo)
SEED-3.md               no tocado
```
No se versionó ni se horneó en imágenes ningún `.env`, DB ni material TLS.

---

## 8. Alcance
- Esta tarea cubre build/up/health/HTTPS/redirect/proxy + **una** llamada TLS representativa
  (`/api/accounts`). Persistencia-tras-reinicio, fail-closed-quitando-una-clave y
  banca/MFA/beneficiario/`verify_chain` son **Tarea 29**.
- Decisiones D-E3-01..04 preservadas. Sin referencias a otras metodologías de spec.

## 9. Recomendación para cerrar el FAIL (Tarea 27)
Añadir a `nginx` una segunda red **no interna** (p. ej. `edge: { internal: false }`) y dejar
`backend` únicamente en `shiftnet` (`internal: true`). Así nginx recibe tráfico del host por sus
puertos publicados y el backend permanece aislado. Corregir también el comentario del compose que
afirma (incorrectamente) que una red interna basta para publicar puertos al host.
