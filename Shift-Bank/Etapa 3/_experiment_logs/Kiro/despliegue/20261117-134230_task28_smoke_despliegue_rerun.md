# Tarea 28 (auto)(verificación) — Smoke de despliegue (RE-EJECUCIÓN sobre artefacto CORREGIDO)

- **Fecha/hora**: 2026-11-17 13:42 (local) · ~18:35–18:42 UTC
- **Workspace**: `Etapa 3\Kiro`
- **Spec**: `.kiro/specs/shift-bank-stage3` · **Requisitos**: R13.1, R13.2 · **Diseño**: §4.4 · **AC**: AC-12
- **Entorno real**: Docker Engine **29.9.3**, Docker Compose **v5.7.0**, OpenSSL (host Windows/PowerShell)
- **Proyecto Compose aislado**: `-p shiftsmoke2` (contenedores/volumen/redes con prefijo `shiftsmoke2_`, 100% desechables)
- **Motivo de la re-ejecución**: el defecto de topología de red probado en la Tarea 28 previa (nginx en una sola red `internal: true`, puertos del host sin enlazar → todo `000`) **ya fue corregido** en la Tarea 27: nginx ahora está en `shiftnet` (interna) **+** `edge` (bridge NO interna); el backend permanece SOLO en `shiftnet` (interna). Esta corrida verifica el artefacto final.

> **VEREDICTO GLOBAL: PASS** — `config`, `build`, `up`, `healthchecks` y TODO el smoke orientado al
> host (HTTPS / redirección HTTP→HTTPS / proxy `/api` sobre TLS / llamada representativa) **PASAN de
> verdad** contra el `docker-compose.yml` corregido. El backend permanece **inalcanzable** desde el
> host (R11.2/AC-12 preservado). Ningún servicio quedó no disponible/no saludable.

---

## 0. Preparación desechable (test-only, git-ignored, borrado al final)

### 0.1 Certificado TLS autofirmado de usar y tirar (`certs/server.crt` + `server.key`)
El OpenSSL del host tiene un `openssl.cnf` potencialmente roto; se apunta `OPENSSL_CONF` a un archivo
temporal vacío para evitarlo. Comando exacto (PowerShell):

```powershell
New-Item -ItemType Directory -Force -Path .\certs | Out-Null
$cfg = New-TemporaryFile; $env:OPENSSL_CONF = $cfg.FullName
openssl req -x509 -newkey rsa:2048 -nodes `
  -keyout .\certs\server.key -out .\certs\server.crt `
  -days 2 -subj "/CN=localhost" `
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
Remove-Item $cfg.FullName -Force; Remove-Item Env:\OPENSSL_CONF
```
`openssl_exit=0`. Verificación del cert generado:
```
subject=CN=localhost
issuer=CN=localhost
notBefore=Nov 17 18:35:18 2026 GMT
notAfter =Nov 19 18:35:18 2026 GMT   (2 días)
X509v3 Subject Alternative Name: DNS:localhost, IP Address:127.0.0.1
server.crt = 1100 bytes · server.key = 1736 bytes
```
Al ser autofirmado se usa `curl -k` en todo el smoke HTTPS (verificación de cadena deshabilitada
a propósito; cert de prueba, no una CA confiable).

### 0.2 `.env` de usar y tirar (secretos de prueba)
```
SHIFT_ENC_KEYS=test:c2hpZnQtYmFuay1zdGFnZTMtdGVzdC1rZXktMzJieXQ=
SHIFT_ENC_ACTIVE_KID=test
SHIFT_AUDIT_HMAC_KEY=dGVzdC1hdWRpdC1obWFjLWtleS1zdGFnZTMtc21va2U=
SHIFT_ADMIN_TOKEN=test-admin-token-stage3-smoke
```
Validaciones previas:
- `SHIFT_ENC_KEYS` decodifica base64 a **exactamente 32 bytes** → `enc_key_bytes=32` ✓ (fail-closed OK)
- `git check-ignore .env certs/server.crt certs/server.key` → los tres **ignorados** por git ✓

---

## 1. `docker compose -p shiftsmoke2 config` → **PASS** (exit 0)
Confirmaciones clave del render:
- 4 secretos interpolados desde `.env` (`SHIFT_ENC_KEYS/_ACTIVE_KID/_AUDIT_HMAC_KEY/_ADMIN_TOKEN`).
- `backend`: **sin** bloque `ports` → NO publicado al host; red `shiftnet` únicamente.
- `nginx`: publica `443:443` y `80:80`; redes `edge` **+** `shiftnet`; monta `./certs:/etc/nginx/certs:ro`;
  `depends_on backend condition: service_healthy`.
- Redes: `shiftsmoke2_shiftnet` `internal: true`; `shiftsmoke2_edge` `driver: bridge` (NO interna).
- Volumen nombrado `shiftsmoke2_shift_db_data`.

## 2. `docker build --no-cache` de ambas imágenes → **PASS**
Builds REALES desde cero (`--no-cache`), capturados con `--progress=plain`:
- **backend** (`shift-bank-backend:stage3`): `apt` curl, `pip install -r requirements.txt`
  (fastapi 0.115.5, uvicorn 0.32.1, pydantic 2.10.3, cryptography 50.0.2, …), symlink entrypoint,
  usuario no root. `naming to docker.io/library/shift-bank-backend:stage3 done`. **`BACKEND_BUILD_EXIT=0`**.
- **frontend** (`shift-bank-frontend:stage3`): `npm ci` + `npm run build` (`tsc && vite build`,
  41 módulos transformados, `built in 976ms`), runtime nginx:1.27-alpine sirviendo `dist/`.
  `naming to docker.io/library/shift-bank-frontend:stage3 done`. **`FRONTEND_BUILD_EXIT=0`**.
Sin DB ni secretos horneados (`.dockerignore` excluye `*.db`, `.env`, certs).

## 3. `docker compose -p shiftsmoke2 up -d` → **PASS (arranque)** (exit 0)
Secuencia real (log): redes `shiftnet`+`edge` Created → volumen Created → `backend Started → Waiting`
(nginx respeta `depends_on: service_healthy`) → `nginx Started`.

## 4. Healthchecks → **PASS**
```
docker compose -p shiftsmoke2 ps
SERVICE   STATUS                    PORTS
backend   Up 52 seconds (healthy)   8000/tcp                               <- 8000 INTERNO (no publicado)
nginx     Up 46 seconds (healthy)   0.0.0.0:80->80/tcp, [::]:80->80/tcp,
                                     0.0.0.0:443->443/tcp, [::]:443->443/tcp <- publicados al host
docker inspect .State.Health.Status   backend=healthy   nginx=healthy
```
Topología verificada (la corrección funciona):
```
docker port shiftsmoke2-nginx-1
  80/tcp  -> 0.0.0.0:80  / [::]:80
  443/tcp -> 0.0.0.0:443 / [::]:443            <- puertos ENLAZADOS al host
nginx networks   = shiftsmoke2_edge  shiftsmoke2_shiftnet   (DOS redes)
backend networks = shiftsmoke2_shiftnet                     (SOLO interna)
backend .NetworkSettings.Ports = {"8000/tcp": null}         (sin binding al host)
shiftnet internal = true     edge internal = false
```

## 5. Smoke orientado al host — **PASS (4/4)** (salida real)
```
1) HTTPS SPA        curl -k https://localhost/
   → http_code=200 content_type=text/html                              PASS
   body: <!doctype html><html lang="es"> … (index.html del build Vite)
2) HTTP->HTTPS      curl -s -o NUL -w "%{http_code} %{redirect_url}" http://localhost/
   → http_code=301 redirect_url=https://localhost/                     PASS
   headers crudos: HTTP/1.1 301 Moved Permanently; Server: nginx/1.27.5; Location: https://localhost/
3) /api sobre TLS   curl -k https://localhost/api/accounts
   → http_code=200 content_type=application/json                       PASS
   body: {"accounts":[{"name":"Checking","balance":"5000000.00"},
                      {"name":"Savings","balance":"15000000.00"}]}      (seed REAL proxied por TLS)
4) backend NO expuesto  curl http://localhost:8000/api/accounts
   → http_code=000, curl_exit=7 (conexión rechazada)                   PASS (correcto: aislado)
```

## 6. Veredictos por check

| Check | Requisito | Resultado (compose CORREGIDO) |
|-------|-----------|-------------------------------|
| `docker compose config` | R13.1 | **PASS** (exit 0) |
| `docker compose build` (ambas imágenes, `--no-cache`) | R13.1 | **PASS** (exit 0×2) |
| `docker compose up -d` | R13.1 | **PASS** (exit 0) |
| Healthchecks backend+nginx `healthy` | R13.1 | **PASS** |
| HTTPS `curl -k https://localhost/` | R13.2 | **PASS** (200 text/html) |
| Redirección HTTP→HTTPS | R13.2 | **PASS** (301 → https://localhost/) |
| Proxy `/api` sobre TLS (llamada representativa) | R13.2 | **PASS** (200 JSON seed real) |
| Backend NO expuesto en host:8000 | R11.2/AC-12 | **PASS** (000, exit 7, rechazado) |

**GLOBAL: PASS** sobre el artefacto final. La corrección de topología de la Tarea 27 (nginx en
`shiftnet`+`edge`; backend solo en `shiftnet` interna) resuelve el defecto previo: R13.2 pasa sin
override, con el backend aún inalcanzable desde el host.

---

## 7. Teardown y limpieza (confirmado)
```
docker compose -p shiftsmoke2 down -v   → exit 0
  nginx Stopped/Removed; backend Stopped/Removed;
  Volume shiftsmoke2_shift_db_data Removed; Network edge Removed; Network shiftnet Removed
docker ps -a  / volume ls / network ls  (filtro shiftsmoke2)  → (vacío en los tres)
```
Borrado de artefactos desechables:
```
env_absent=True        (.env borrado)
certs_absent=True      (certs/ borrado)
raíz workspace: .kiro, backend, frontend, loadtest, .env.example, .gitignore, docker-compose.yml
```
Datos históricos intactos:
```
backend/shift_bank.db  SHA256 = 33E74D26F33D13449AA658171D50CFF65453FEFC57E20373D118E534243353CC
  (idéntico al esperado antes y después; el stack usó el volumen Docker desechable, nunca este archivo)
SEED-3.md               SHA256 = 99D23B7AEE6EEB775FDC1617FFF46A5409F10CB779EBCF411245E4602FABF1D9  (no tocado)
```
`git status --porcelain`: **ningún** `.env`, cert o `*.db` en staging/tracking; nada secreto versionado.

---

## 8. Alcance
- Esta tarea cubre build/up/health/HTTPS/redirect/proxy + **una** llamada TLS representativa
  (`/api/accounts`). Persistencia-tras-reinicio, fail-closed-quitando-una-clave y
  banca/MFA/beneficiario/`verify_chain` son **Tarea 29**, no aquí.
- Decisiones D-E3-01..04 preservadas. Sin referencias a otras metodologías de spec.
