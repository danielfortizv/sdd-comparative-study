# Tarea 27 (corrección) — Fix de topología de red en `docker-compose.yml` (defecto probado por T28)

- **Fecha/hora**: 2026-11-17 13:31 (local)
- **Workspace**: `Etapa 3\Kiro`
- **Spec**: `.kiro/specs/shift-bank-stage3` · **Requisitos**: R11.1, R11.2, R13.1, R13.2 · **Diseño**: §4.1, §4.3, §4.4 · **AC**: AC-12
- **Entorno real**: Docker Engine **29.9.3**, Docker Compose **v5.7.0**, OpenSSL **3.3.0** (host Windows/PowerShell)
- **Evidencia del defecto**: `20261117-131027_task28_smoke_despliegue.md`
- **Decisiones preservadas**: D-E3-01..04. Sin referencias a otras metodologías de spec.

> **VEREDICTO: PASS** — Aplicada EXCLUSIVAMENTE la corrección de topología de red (añadir una red
> NO interna `edge` solo a nginx) más la corrección del comentario engañoso. Verificado de verdad:
> `docker compose config` exit 0 con la topología correcta, y re-verificación host-facing real
> (HTTPS 200 / redirect 301 / `/api` 200 JSON seed / backend :8000 rechazado). Teardown confirmado.

---

## 1. El defecto (probado por T28)

Con el compose de la Tarea 27 tal cual, `nginx` estaba en UNA SOLA red, `shiftnet`, que es
`internal: true`. En este motor Docker, un contenedor cuya **única** red es interna NO puede
enlazar sus puertos publicados al host (no hay ruta de NAT host ↔ red interna):
`docker port` vacío; `.NetworkSettings.Ports` = `{"443/tcp":[],"80/tcp":[]}`. Resultado: todos los
checks host-facing (HTTPS, redirección, proxy `/api`) devolvían `http_code=000`.

El comentario del compose afirmaba (incorrectamente) que los puertos publicados de nginx son
"NAT del host y no dependen de que la red tenga salida" — falso en la práctica para este caso.

## 2. El fix (diff exacto de YAML)

**(a) nginx — adjuntado a AMBAS redes (antes: solo `shiftnet`):**
```diff
     ports:
       - "443:443"
       - "80:80"
+    # DOS redes: `shiftnet` (interna) para reach al upstream `backend`, y `edge` (NO interna)
+    # para que los puertos publicados 443/80 se enlacen al host. Sin `edge`, un contenedor cuya
+    # única red es `internal: true` no obtiene binding de host (puertos sin publicar de verdad).
     networks:
       - shiftnet
+      - edge
```

**(b) Nueva red `edge` NO interna (backend SIN cambios, sigue solo en `shiftnet`):**
```diff
 networks:
   shiftnet:
     driver: bridge
     internal: true
+  edge:
+    driver: bridge
+    internal: false
```

**(c) Comentarios corregidos** (cabecera de topología §4.1 + bloque `networks`): se reemplazó la
afirmación errónea ("los puertos publicados son NAT del host y no dependen de que la red tenga
salida") por la explicación correcta: una red `internal: true` NO tiene ruta de NAT al host, así
que nginx necesita la red NO interna `edge` para publicar 443/80; el `backend` permanece solo en
`shiftnet` (interna) y por tanto inalcanzable desde el host (R11.2, AC-12).

**NO se tocó nada más**: exactamente dos servicios; `backend` SIN `ports` y con UNA sola réplica
(sin `deploy.replicas`); secretos por entorno (`env_file` + `${VAR}` sin literales); volumen
nombrado `shift_db_data:/data`; bind de certs `./certs:/etc/nginx/certs:ro`; `depends_on backend
condition: service_healthy`; healthcheck.

## 3. `docker compose config` → **PASS** (exit 0)

```
docker compose -p shiftfix config   →  exit 0
```
Confirmado en el config renderizado:
- Red `edge` presente, bridge, **sin** `internal` (=> `internal: false`).
- Red `shiftnet` sigue `internal: true`.
- `nginx.networks` = `[edge, shiftnet]`; `backend.networks` = `[shiftnet]` ÚNICAMENTE.
- `backend` SIN bloque `ports`; `nginx` publica `443` y `80`.
- Sin `deploy.replicas` → una sola réplica de backend (un scheduler).
- Secretos interpolados desde `.env` (4 variables, sin literales en el fuente).
- Volumen `shift_db_data` → `/data`; bind `certs` → `/etc/nginx/certs` (read_only).

Binding real de puertos (antes vacío, AHORA enlazado al host):
```
docker port shiftfix-nginx-1
  80/tcp  -> 0.0.0.0:80   / [::]:80
  443/tcp -> 0.0.0.0:443  / [::]:443
docker inspect redes nginx   → shiftfix_edge shiftfix_shiftnet
docker inspect redes backend → shiftfix_shiftnet         (solo interna)
```

## 4. Re-verificación host-facing REAL (proyecto aislado `-p shiftfix`, volumen desechable)

Preparación desechable (test-only, git-ignorada, borrada al final):
- `.env` de prueba estilo conftest: `SHIFT_ENC_KEYS=test:c2hpZnQtYmFuay1zdGFnZTMtdGVzdC1rZXktMzJieXQ=`
  (decodifica a **exactamente 32 bytes**), `SHIFT_ENC_ACTIVE_KID=test`,
  `SHIFT_AUDIT_HMAC_KEY=dGVzdC1hdWRpdC1obWFjLWtleS1zdGFnZTMtc21va2U=`,
  `SHIFT_ADMIN_TOKEN=test-admin-token-stage3-smoke`.
- Cert autofirmado de usar y tirar `./certs/server.{crt,key}` (CN=localhost, SAN DNS:localhost +
  IP:127.0.0.1, 2 días). `git check-ignore` confirmó `.env`, `certs/server.crt`, `certs/server.key`
  todos ignorados.

`docker compose -p shiftfix up -d --build` → exit 0. Secuencia real: backend Started → Waiting →
Healthy, luego nginx Started. Ambos servicios `healthy`.

Resultados REALES (ambos servicios healthy):
```
1) HTTPS SPA        curl -k https://localhost/
   → http_code=200 content_type=text/html                                   PASS
2) HTTP->HTTPS      curl http://localhost/
   → http_code=301 redirect_url=https://localhost/                          PASS
3) /api sobre TLS   curl -k https://localhost/api/accounts
   → http_code=200 content_type=application/json                            PASS
   body: {"accounts":[{"name":"Checking","balance":"5000000.00"},
                      {"name":"Savings","balance":"15000000.00"}]}           (seed real proxied)
4) backend NO expuesto  curl http://localhost:8000/api/accounts
   → http_code=000, curl_exit=7 (conexión rechazada)                        PASS (aislado)
```

Backend permanece inalcanzable desde el host (solo en `shiftnet` interna): R11.2 / AC-12 preservado.

## 5. Teardown y limpieza (confirmado)

```
docker compose -p shiftfix down -v   → exit 0
  contenedores shiftfix-backend-1 / shiftfix-nginx-1 REMOVIDOS
  volumen shiftfix_shift_db_data REMOVIDO
  redes shiftfix_shiftnet y shiftfix_edge REMOVIDAS
docker ps -a / volume ls / network ls (filtro shiftfix) → (vacío en los tres)
```
Artefactos desechables borrados:
```
env_absent=True        (.env borrado)
certs_absent=True      (certs/ borrado)
config_render.txt      (temporal de verificación, borrado)
```
No se versionó ni se horneó en imágenes ningún `.env`, DB ni material TLS.

Datos históricos intactos:
```
backend/shift_bank.db  SHA256 = 33E74D26F33D13449AA658171D50CFF65453FEFC57E20373D118E534243353CC
  (idéntico antes y después; el stack usó el volumen Docker desechable, nunca este archivo)
SEED-3.md               no tocado
```

## 6. Alcance
- Corrección ÚNICA: topología de red de nginx (+ comentario). No se tocó la garantía de un solo
  scheduler/una réplica, el aislamiento del backend, el manejo de secretos, el volumen ni el mount
  de certs. Decisiones D-E3-01..04 preservadas.
