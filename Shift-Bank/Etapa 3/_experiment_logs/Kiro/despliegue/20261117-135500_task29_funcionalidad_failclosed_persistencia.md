# Tarea 29 (auto)(verificación) — Funcionalidad, fail-closed y persistencia tras reinicio

- **Fecha/hora**: 2026-11-17 ~13:45–13:55 (local, UTC-05) · ~18:45–18:55 UTC
- **Workspace**: `Etapa 3\Kiro`
- **Spec**: `.kiro/specs/shift-bank-stage3` · **Requisitos**: R12.2, R13.3, R13.4, R13.5, R13.6 · **Diseño**: §4.3, §4.4 · **AC**: AC-12, AC-13
- **Decisiones honradas**: D-E3-01 (cifrado de campo AES-GCM en reposo, token `enc:v1:...`, sin fallback a texto plano, claves externas por entorno), D-E3-02 (cadena de auditoría HMAC append-only, verificación vía endpoint protegido por `X-Admin-Token`), D-E3-04 (topología Compose, fail-closed, volumen persistente)
- **Entorno real**: Docker Engine **29.9.3**, Docker Compose **v5.7.0**, OpenSSL (host Windows/PowerShell)
- **Proyecto Compose aislado**: `-p shiftt29` (contenedores/volumen/redes con prefijo `shiftt29_`, 100% desechables)
- **Precondición**: T28 (smoke) PASS — topología corregida (nginx en `shiftnet`+`edge`, backend solo `shiftnet` interna).

> **VEREDICTO GLOBAL: PASS** — Las cinco sub-verificaciones (A banca/MFA, B token `enc:` en la DB del
> volumen, C `verify_chain` + auth fail-closed, D arranque fail-closed al quitar una clave, E persistencia
> de datos cifrados + cadena de auditoría tras reinicio en el MISMO volumen) se demostraron **de verdad**
> contra el stack desplegado por HTTPS. Volúmenes desechables; datos históricos intactos; sin secretos/certs
> versionados.

---

## 0. Preparación desechable (test-only, git-ignored, borrado al final)

### 0.1 Certificado TLS autofirmado de usar y tirar (`certs/server.crt` + `server.key`)
El OpenSSL del host puede tener un `openssl.cnf` roto; se apunta `OPENSSL_CONF` a un archivo temporal
vacío. Comando exacto (PowerShell):

```powershell
New-Item -ItemType Directory -Force -Path .\certs | Out-Null
$cfg = New-TemporaryFile; $env:OPENSSL_CONF = $cfg.FullName
openssl req -x509 -newkey rsa:2048 -nodes `
  -keyout .\certs\server.key -out .\certs\server.crt `
  -days 2 -subj "/CN=localhost" `
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
Remove-Item $cfg.FullName -Force; Remove-Item Env:\OPENSSL_CONF
```
`openssl_exit=0` · `crt_bytes=1100` · `key_bytes=1732`. Autofirmado → todo el smoke HTTPS usa `curl -k`.

### 0.2 `.env` de usar y tirar (secretos SOLO de prueba)
```
SHIFT_ENC_KEYS=test:c2hpZnQtYmFuay1zdGFnZTMtdGVzdC1rZXktMzJieXQ=
SHIFT_ENC_ACTIVE_KID=test
SHIFT_AUDIT_HMAC_KEY=dGVzdC1hdWRpdC1obWFjLWtleS1zdGFnZTMtdGFzazI5
SHIFT_ADMIN_TOKEN=test-admin-token-stage3
```
Validaciones previas:
- `SHIFT_ENC_KEYS` decodifica base64 a **exactamente 32 bytes** → `enc_key_bytes=32` ✓ (AES-256, fail-closed OK)
- `git check-ignore .env certs/server.crt certs/server.key` → los tres **ignorados** por git ✓

### 0.3 Arranque
```
docker compose -p shiftt29 config    → config_exit=0 (4 secretos interpolados; backend sin ports; shiftnet internal:true; edge no interna; volumen shiftt29_shift_db_data)
docker compose -p shiftt29 up -d --build   → up_exit=0
```
Estado tras `up`:
```
SERVICE   STATUS                    PORTS
backend   Up (healthy)              8000/tcp                 <- INTERNO, no publicado al host
nginx     Up (healthy)             0.0.0.0:80->80, 0.0.0.0:443->443
backend health=healthy   nginx health=healthy
docker port shiftt29-nginx-1 → 80->0.0.0.0:80 / 443->0.0.0.0:443 (enlazados al host)
```

---

## A) OPERACIÓN BANCARIA + MFA — **PASS**

Cuentas iniciales (seed): Checking `5000000.00`, Savings `15000000.00`.

### A.1 Transferencia pequeña (< umbral MFA 1.000.000) → completa directo
```
POST https://localhost/api/transfers  {"from":"checking","to":"savings","amount":"50000","description":"T29 small direct"}
→ HTTP 201  {"status":"COMPLETED","mfa_required":false,"reference":null,"expires_at":null}
```

### A.2 Transferencia >= umbral → PENDING_MFA → confirmar 123456 → COMPLETED
```
POST https://localhost/api/transfers  {"from":"savings","to":"checking","amount":"1500000","description":"T29 MFA transfer"}
→ HTTP 201  {"status":"PENDING_MFA","mfa_required":true,"reference":"6e272b3702f74f54b249b21e2d65bd1c","expires_at":"2026-11-17T18:53:02Z"}

POST https://localhost/api/transfers/6e272b3702f74f54b249b21e2d65bd1c/mfa  {"code":"123456"}
→ HTTP 200  {"status":"COMPLETED"}
```
Saldos tras A: Checking `6450000.00` (+1.500.000 −50.000), Savings `13550000.00`. El dinero se movió de
verdad y de forma consistente; el umbral de MFA se ejerció (reference real + confirmación con el código fijo).

**A: PASS** — transferencia directa + flujo MFA completo verificados sobre el stack TLS.

---

## B) CREACIÓN DE BENEFICIARIO + token `enc:` en la DB del VOLUMEN — **PASS**

### B.1 Alta por API (respuesta enmascarada)
```
POST https://localhost/api/beneficiaries  {"name":"Maria Lopez","bank":"Bancolombia","routing_number":"021000021","account_number":"1234567890"}
→ HTTP 201  {"id":"a4df78ec-44ef-4271-ad25-5e68878390b9","name":"Maria Lopez","bank":"Bancolombia","routing_number":"021000021","account_masked":"••••7890"}
```
Además se creó una ACH al beneficiario para poblar el `beneficiary_snapshot` cifrado:
```
POST https://localhost/api/ach  {"amount":"25000","description":"T29 ACH to bene","from":"checking","beneficiary_id":"a4df78ec-..."}
→ HTTP 201  {"status":"pending","mfa_required":false,"reference":"5d4d03c84b1545f4b3921d8364e4f347","expires_at":null}
```

### B.2 Inspección de la DB DENTRO del volumen (`/data/shift_bank.db`)
Ejecutado vía `docker exec -i shiftt29-backend-1 python -` (lectura directa de columnas crudas):
```
DB_FILE: /data/shift_bank.db
beneficiary (raw):
  Maria Lopez | Bancolombia
    account_number prefix: enc:v1:test:   full_len=65   is_enc=True   plaintext '1234567890' present? False
    routing_number prefix: enc:v1:test:   full_len=65   is_enc=True   plaintext '021000021'  present? False
transfer.beneficiary_snapshot (type=ach):
  ref 5d4d03c84b1545f4b3921d8364e4f347  prefix: enc:v1:test:  full_len=197  is_enc=True  plaintext '1234567890' present? False
```
Los tres campos sensibles (account_number, routing_number, beneficiary_snapshot) están almacenados como
**ciphertext `enc:v1:test:...`**, NO en texto plano. (Prefijo mostrado; ciphertext completo NO impreso.)

**B: PASS** — cifrado en reposo real; ningún identificador bancario sensible en claro en el volumen.

---

## C) AUDITORÍA `verify_chain` + fail-closed de autorización — **PASS**

```
GET  https://localhost/api/audit/verify   -H "X-Admin-Token: test-admin-token-stage3"
  → HTTP 200  {"ok":true}
POST https://localhost/api/audit/verify   -H "X-Admin-Token: test-admin-token-stage3"
  → HTTP 200  {"ok":true}
GET  https://localhost/api/audit/verify   -H "X-Admin-Token: wrong-token"
  → HTTP 401  {"error":{"code":"UNAUTHORIZED","message":"Credencial administrativa requerida"}}
GET  https://localhost/api/audit/verify   (sin cabecera)
  → HTTP 401  {"error":{"code":"UNAUTHORIZED","message":"Credencial administrativa requerida"}}
```
Cadena íntegra (incluida el ancla) con token válido; sin token / token erróneo → 401 (sin bypass, sin
filtrar el veredicto). `hmac.compare_digest` en tiempo constante.

**C: PASS** — `verify_chain` ok:true protegido; acceso fail-closed demostrado.

---

## D) FAIL-CLOSED (negativo): quitar una clave impide el arranque — **PASS**

Secuencia (volumen PRESERVADO; `down` SIN `-v`):
```
docker compose -p shiftt29 down           → exit 0  (contenedores removidos; volumen shiftt29_shift_db_data CONSERVADO)
# .env respaldado a .env.bak; se reescribe .env SIN la línea SHIFT_ENC_KEYS
docker compose -p shiftt29 up -d --no-deps backend
```
Compose avisa de la variable ausente:
```
level=warning msg="The \"SHIFT_ENC_KEYS\" variable is not set. Defaulting to a blank string."
      SHIFT_ENC_KEYS: ""
```
El backend NO llega a healthy — crash-loop (`Restarting (3)`), exit 3. Log real del fallo (fail-closed, R12.2):
```
  File "/app/app/main.py", line 53, in lifespan
    config.validate_startup_config()
  File "/app/app/config.py", line 183, in validate_startup_config
    _validate_enc_keys()
  File "/app/app/config.py", line 117, in _validate_enc_keys
    raise ConfigError(f"{ENV_ENC_KEYS} ausente o vacío: se requiere para cifrado en reposo")
app.config.ConfigError: SHIFT_ENC_KEYS ausente o vacío: se requiere para cifrado en reposo
ERROR:    Application startup failed. Exiting.
```
Verificación de que nginx nunca obtiene un backend sano:
```
docker ps -a --filter name=shiftt29  → SOLO shiftt29-backend-1 (Restarting)
nginx_container='' (ausente)   # depends_on: service_healthy nunca se satisface
```
Luego se **restauró el `.env` completo** desde `.env.bak` (y se borró `.env.bak`).

**D: PASS** — una clave requerida ausente IMPIDE realmente el arranque (ConfigError en `lifespan`); nginx no
arranca su dependencia. El material de clave nunca aparece en el error (solo el nombre de la variable).

---

## E) PERSISTENCIA TRAS REINICIO (mismo volumen) — **PASS**

Con el `.env` completo restaurado y el MISMO volumen nombrado (sin `down -v` entre la escritura de B/C y el
reinicio), se levantó de nuevo el stack:
```
docker compose -p shiftt29 up -d   → up_exit=0;  backend Healthy, nginx Started
```
Evidencia tras el reinicio:
```
GET /api/beneficiaries → {"beneficiaries":[{"id":"a4df78ec-...","name":"Maria Lopez","bank":"Bancolombia","routing_number":"021000021","account_masked":"••••7890"}]}
GET /api/accounts      → Checking 6425000.00 (6.450.000 − 25.000 ACH), Savings 13550000.00   (NO reseteado al seed 5M/15M → datos del volumen sobrevivieron)
GET /api/audit/verify (token válido) → HTTP 200 {"ok":true}
DB del volumen (post-reinicio):
  bene Maria Lopez | acct prefix enc:v1:test: is_enc=True | routing prefix enc:v1:test: is_enc=True
  ach snap 5d4d03c84b1545f4b3921d8364e4f347 | prefix enc:v1:test: is_enc=True
  audit_log entries: 6
```
Confirmación adicional con `docker compose -p shiftt29 restart` (reinicio simple): `verify_chain` ok:true,
beneficiario presente, saldos preservados.

**E: PASS** — datos cifrados (`enc:`-prefijados) y la cadena de auditoría (`verify_chain` ok:true, 6 entradas)
SOBREVIVEN al reinicio en el mismo volumen (R13.4). Los saldos reflejan la actividad previa, probando que NO
es un volumen nuevo.

---

## Veredictos por sub-check

| Sub-check | Requisito | Resultado |
|-----------|-----------|-----------|
| A — Operación bancaria directa + flujo MFA (PENDING_MFA → 123456 → COMPLETED) | R13.3 | **PASS** |
| B — Alta de beneficiario + token `enc:v1:test:` en la DB del volumen (3 campos) | R13.3, R13.5 | **PASS** |
| C — `verify_chain` ok:true (GET/POST) + 401 sin/mal token (fail-closed auth) | R13.3 | **PASS** |
| D — Quitar `SHIFT_ENC_KEYS` → ConfigError en `lifespan`, backend no healthy, nginx ausente | R12.2, R13.6 | **PASS** |
| E — Datos cifrados + cadena de auditoría sobreviven al reinicio (mismo volumen) | R13.4 | **PASS** |

**GLOBAL: PASS.**

---

## Teardown y limpieza (confirmado)
```
docker compose -p shiftt29 down -v    → exit 0 (contenedores/redes/VOLUMEN desechable removidos)
residual shiftt29: containers (vacío) · volumes (vacío) · networks (vacío)
Remove-Item .env ; Remove-Item certs -Recurse ; (.env.bak ya borrado al restaurar)
env_absent=True   certs_absent=True   envbak_absent=True
raíz workspace: .env.example, .gitignore, .kiro, backend, docker-compose.yml, frontend, loadtest
```

## Datos históricos intactos / nada secreto versionado
```
backend/shift_bank.db SHA256 = 33E74D26F33D13449AA658171D50CFF65453FEFC57E20373D118E534243353CC   (IDÉNTICO al esperado — el stack usó el volumen Docker desechable, nunca este archivo)
SEED-3.md             SHA256 = 99D23B7AEE6EEB775FDC1617FFF46A5409F10CB779EBCF411245E4602FABF1D9   (no tocado)
git status --porcelain: `Etapa 3/Kiro/` figura como directorio NO rastreado; NINGÚN .env, cert o *.db
  individual en staging/tracking. Nada secreto/cert/db versionado.
```

## Alcance
- Esta tarea verifica funcionalidad end-to-end (banca/MFA/cifrado/auditoría), fail-closed de arranque y
  persistencia tras reinicio sobre el stack Compose desplegado. Todo con volúmenes desechables aislados.
- Decisiones D-E3-01..04 preservadas. Sin cambios de código de la app; sin referencias a otras metodologías de spec.
