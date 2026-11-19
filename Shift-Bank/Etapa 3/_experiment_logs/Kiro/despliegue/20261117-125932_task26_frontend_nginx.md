# Tarea 26 — Build del frontend y servicio Nginx (TLS + proxy + redirect)

- **Fecha/hora (local):** 2026-11-17 12:59:32 (-05:00)
- **Workspace:** `Etapa 3/Kiro`
- **Spec:** `.kiro/specs/shift-bank-stage3` · Requisitos R4.1, R4.2, R4.3, R4.4, R11.1, R11.2 ·
  Diseño §1.7, §4.1, §4.2 · AC-12
- **Decisión honrada:** D-E3-04 (Docker Compose local: backend + Nginx con terminación TLS,
  reverse-proxy, redirección HTTP→HTTPS, red interna, secretos por entorno, fail-closed, volumen
  persistente, un solo scheduler, no-root, **SOLO verificación local**). Preserva D-E3-01..04.
- **Tipo de spec:** no-bugfix (workflow feature; no hay `.config` con `specType: bugfix`).
- **Entorno:** Docker 29.9.3 · Node v20.17.0 · npm 11.6.3 · Windows.

## Archivos creados / modificados

| Archivo | Acción | Propósito |
| --- | --- | --- |
| `frontend/src/api/client.ts` | **MOD** | Origen base de la API RELATIVO por defecto (ver diff). Única línea de lógica cambiada. |
| `frontend/src/vite-env.d.ts` | **NUEVO** | Tipado de `import.meta.env.VITE_API_BASE_URL` (+`vite/client`). Solo tipos. |
| `frontend/Dockerfile` | **NUEVO** | Multistage: Node build (`npm ci`+`npm run build`) → Nginx sirve `dist/`. |
| `frontend/nginx.conf` | **NUEVO** | HTTPS 443 (certs montados), redirección 80→443 (301), SPA fallback, reverse-proxy `/api`→`http://backend:8000`. |
| `frontend/.dockerignore` | **NUEVO** | Excluye `node_modules`, `dist`, `.env`, certs, `.git`. |
| `frontend/.env.example` | **NUEVO** | Documenta `VITE_API_BASE_URL` (default relativo). |
| `frontend/.gitignore` | **MOD** | Añade exclusión de `.env*` (salvo `.env.example`) y material TLS. |

## Cambio de origen relativo en el frontend (diff exacto de client.ts)

Única modificación de lógica. NO se cambió ninguna ruta, método, cuerpo ni la función
`request()`; solo la resolución del origen base.

```diff
-const BASE_URL = "http://localhost:8000";
+// Origen base de la API. En el build de producción (servido por Nginx) debe ser RELATIVO
+// (cadena vacía): así `${BASE_URL}/api/...` resuelve a `/api/...` contra el MISMO origen HTTPS
+// de la página, y Nginx hace reverse-proxy de `/api` al backend por la red interna de Docker
+// (Etapa 3, Tarea 26; diseño §1.7, §4.2). Para el desarrollo local se puede sobreescribir con
+// la variable de entorno de Vite `VITE_API_BASE_URL` (p. ej. "http://localhost:8000"); el
+// DEFAULT es relativo para que el despliegue Docker/Nginx sea correcto sin configuración extra.
+// No se cambia ninguna ruta, método, cuerpo ni la lógica de `request()`: solo el origen base.
+const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
```

- Con el default (`""`), `request("/api/accounts")` llama a `fetch("/api/accounts")` → origen
  relativo = mismo host HTTPS que sirve la página → Nginx proxya al backend (R4, R11, R14.4).
- `src/vite-env.d.ts` añade `/// <reference types="vite/client" />` y tipa
  `VITE_API_BASE_URL?: string` para que `tsc` (que corre antes de `vite build`) compile en modo
  `strict`. Es solo tipado; no altera comportamiento.
- `.env.example` documenta la variable; en producción se deja SIN definir (default relativo), por
  lo que el build Docker/Nginx es correcto "out of the box".

## Dockerfile multistage (`frontend/Dockerfile`)

- **Etapa 1 `build` (`node:20-alpine`):** `COPY package*.json` → `npm ci` (lockfile) →
  `COPY . .` → `npm run build` (`tsc && vite build`) → assets en `/app/dist`. El build usa el
  default relativo (sin `VITE_API_BASE_URL`).
- **Etapa 2 `runtime` (`nginx:1.27-alpine`):** elimina `default.conf`, copia `nginx.conf` a
  `/etc/nginx/conf.d/shift-bank.conf`, copia `--from=build /app/dist` a
  `/usr/share/nginx/html`. Crea `/etc/nginx/certs` (punto de montaje de certs) con ownership
  `nginx:nginx`. `EXPOSE 80 443`. HEALTHCHECK `wget --no-check-certificate https://127.0.0.1/`.
- **No-root (R11.4, "donde sea factible"):** el proceso MAESTRO de Nginx arranca como root solo
  para enlazar los puertos privilegiados 80/443 (requisito del kernel para puertos <1024); los
  procesos WORKER que atienden tráfico corren como el usuario NO privilegiado `nginx` (directiva
  `user nginx;` de la imagen oficial). Se descartó la variante unprivileged (8080/8443) para
  conservar el contrato de exponer 80/443 (diseño §4.2). Compromiso documentado explícitamente.
- Certs NUNCA horneados: el `.dockerignore` excluye `*.pem/*.key/*.crt/*.p12/*.pfx` y `certs/`
  (R4.4); se montan en runtime en `/etc/nginx/certs/` (Tarea 27/28).

## nginx.conf (comportamiento)

- **Terminación HTTPS (443):** `ssl_certificate /etc/nginx/certs/server.crt` +
  `ssl_certificate_key /etc/nginx/certs/server.key` (montados externamente). `http2 on`,
  `ssl_protocols TLSv1.2 TLSv1.3`. (R4.1/R4.4, AC-12)
- **Redirección HTTP→HTTPS (80):** server aparte con `return 301 https://$host$request_uri`.
  (R4.2)
- **Assets estáticos + SPA:** `root /usr/share/nginx/html`, `location / { try_files $uri $uri/
  /index.html; }` para enrutamiento de cliente con recarga directa.
- **Reverse-proxy `/api` (R4.3, R11.1/R11.2):** `location /api/ { proxy_pass
  http://backend:8000; ... }`. El prefijo `/api` se preserva tal cual (el backend monta todas
  sus rutas con `prefix="/api"`; verificado en `backend/app/routers/*.py` y `main.py`). Cabeceras
  `Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto ($scheme)`, `X-Forwarded-Host`;
  `proxy_http_version 1.1` + `Connection ""`.
- **Upstream `backend`:** nombre de servicio resuelto por el DNS interno de Docker Compose; se
  cablea en `docker-compose.yml` (Tarea 27). El backend no publica puertos al host (R11.2).
- **Ruta de certs (mount):** `/etc/nginx/certs/` (volumen/bind en Compose, Tarea 27/28).

## Verificación — ejecutado REAL vs diferido

### PASS (ejecutado de verdad)

1. **`npm run build` en `frontend/`** — **PASS (exit 0)**. `tsc` sin errores + `vite build`
   produjo `dist/index.html`, `dist/assets/index-*.js` (169.82 kB), `dist/assets/index-*.css`
   (4.52 kB). Confirma que el cambio de `client.ts` + `vite-env.d.ts` compila en `strict`.
2. **`docker build -t shift-bank-frontend:task26 .`** — **PASS (exit 0)**. Imagen final 74.2 MB.
   El build real ejecutó `npm ci` + `npm run build` en la etapa Node y ensambló la imagen Nginx.
3. **Sanity de `nginx -t` (parcial, local):**
   - Sin dependencias de runtime, `nginx -t` falla con `host not found in upstream "backend"`
     (línea 63) — esperado: no hay DNS de Compose ni certs montados fuera del stack.
   - Con las DOS dependencias de runtime satisfechas localmente (`--add-host backend:127.0.0.1`
     y un par de certs autofirmados colocados en `/etc/nginx/certs/`), `nginx -t` devuelve
     **"syntax is ok" / "test is successful" (exit 0)**. Esto prueba que el `nginx.conf` es
     sintáctica y estructuralmente válido; el único bloqueo fuera del stack son las dependencias
     de runtime (DNS del servicio `backend` + certs montados).

### DIFERIDO a Tarea 28 (NO ejecutado aquí; NO se reclama PASS)

- Smoke end-to-end de **HTTPS real**, **redirección 80→443** y **proxy `/api`** sobre el stack
  completo (backend + nginx + certs + red interna de Compose). Requiere `docker compose up` con
  ambos servicios y certificados provisionados — es el alcance explícito de la **Tarea 28**.
- No se arrancó el contenedor en modo servicio ni se hicieron peticiones HTTPS/redirect/proxy
  reales de extremo a extremo en esta tarea.

## Trazabilidad

- R4.1 (TLS) ✔ (config + build) · R4.2 (redirect 80→443) ✔ (config) · R4.3 (proxy a red interna)
  ✔ (config; e2e→T28) · R4.4 (certs no horneados) ✔ (.dockerignore/.gitignore) · R11.1 (Nginx
  sirve+proxy) ✔ · R11.2 (backend sin puerto al host) ✔ (contrato de config; stack→T27/28).
- AC-12: terminación HTTPS, redirect y proxy **configurados y validados sintácticamente**; la
  demostración end-to-end queda en T28.

## Notas de seguridad / preservación

- NO se hornean certs ni secretos en la imagen (R4.4): excluidos por `.dockerignore`/`.gitignore`
  y montados en runtime.
- Lógica de peticiones del frontend intacta (solo origen base relativo). Contratos de API y
  comportamiento de la app preservados (R14.4). D-E3-01..04 preservadas.
- Imagen de prueba `shift-bank-frontend:task26` creada solo para verificación local.
