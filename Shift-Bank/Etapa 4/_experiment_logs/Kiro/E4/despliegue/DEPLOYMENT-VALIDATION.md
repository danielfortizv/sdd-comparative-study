# Stage 4 — Validación de despliegue en vivo (Tarea 25) — evidencia real

Reemplaza la nota PARCIAL previa: el despliegue completo se ejecutó y verificó en vivo.

## Entorno y secretos desechables
- Docker 29.9.3, Docker Compose v5.7.0.
- Certificado TLS autofirmado DESECHABLE generado con `cryptography` (CN=localhost, 2 días) en
  `certs/` (git-ignorado). Secretos de prueba en `.env` DESECHABLE (claves de SOLO prueba, no
  secretos reales). Ambos **eliminados** en el cleanup final.

## Build y arranque (real)
- `docker compose build`: exit **0** (imágenes `shift-bank-backend:stage3`,
  `shift-bank-frontend:stage3` — construyen el código de la Etapa 4 desde `backend/`/`frontend/`).
- `docker compose up -d`: exit **0**. `docker compose ps`: **backend healthy**, **nginx healthy**
  (nginx arranca solo tras `backend` sano, `depends_on: service_healthy`).

## Smoke (real, sobre la pila viva)
- **HTTPS** `GET https://localhost/api/v2/accounts` → **200**; devuelve la **fixture D-02 por
  defecto**: CHK-1001 USD 2500.00, SAV-2001 USD 10000.00, EUR-3001 EUR 0.00, GBP-4001 GBP 0.00
  (confirma que la app por defecto expone datos de la Etapa 4).
- **Redirección HTTP→HTTPS**: `GET http://localhost/` → **301 Moved Permanently**,
  `Location: https://localhost/`.
- **Reverse-proxy de API**: Nginx (TLS) → backend por red interna; el backend no publica puertos.
- **Conversión multidivisa por HTTPS**: `POST /api/conversions` (Idempotency-Key) → **200**,
  rate 9/10, 100.00 USD → 90.00 EUR, con `event_ids` compuestos.

## Persistencia, auditoría y fail-closed (real)
- **Persistencia tras reinicio**: antes de `docker compose restart` CHK=2400.00/v2, EUR=90.00/v2;
  después del reinicio **idénticos** → el volumen SQLite `shift_db_data` persiste el estado
  event-sourced (R12.3/R13.4).
- **Integridad de auditoría**: `GET https://localhost/api/audit/verify` (X-Admin-Token) →
  `{"ok":true}`, **200** (cadena HMAC + ancla válidas tras operaciones y reinicio).
- **Datos cifrados en reposo**: el arranque valida claves AES-GCM externas (fail-closed) y la
  app opera; los identificadores sensibles de beneficiarios se cifran en reposo (heredado,
  preservado). (Evidencia de operación cifrada: arranque healthy exige claves válidas.)
- **Fail-closed**: con `.env` de claves VACÍAS, el backend lanza
  `ConfigError: SHIFT_ENC_KEYS ausente o vacío` y "Application startup failed. Exiting."; el
  contenedor queda **Restarting**, nunca healthy → no sirve tráfico.

## Cleanup / estado limpio restaurado
- `docker compose down -v`: exit **0** (contenedores + volumen `shift_db_data` eliminados).
- `.env` y `certs/` eliminados. Verificado: sin contenedores del proyecto, sin volumen, sin
  `.env`/`certs`. Las imágenes construidas se conservan (reutilizables; no son archivos del
  workspace).

## Veredicto
Despliegue local Etapa 4: **PASS** — build/up/health/HTTPS/redirect/proxy/fixture-D02/
conversión/persistencia/auditoría/fail-closed verificados en vivo. Evidencia cruda:
`despliegue/docker-build.txt`, `docker-up.txt`, `docker-ps.txt`, `smoke.txt`, `persistence.txt`,
`docker-restart.txt`, `fail-closed.txt`, `docker-down-final.txt`, `cert-gen.txt`.
```
NOTA: un `docker compose config` por sí solo NO prueba despliegue; esta validación ejecutó el
ciclo completo build/up/smoke/persistencia/fail-closed contra la pila viva.
```
