# Shift Bank local Compose deployment

This is a local, synthetic-data deployment. It uses one FastAPI/Uvicorn backend process (and therefore one scheduler lifecycle) plus an unprivileged Nginx frontend container serving the production Vite assets and terminating HTTPS. The backend has no published host port. Do not add backend replicas: the Compose `container_name` makes the scheduler-bearing service unscalable, and the backend command does not use Uvicorn workers.

## Local prerequisites

- Docker Desktop with Docker Compose v2 or later.
- Python 3.12+ and the repository's `cryptography` dependency for local secret/certificate generation.
- Ports 18080 and 18443 free on loopback.

## Create excluded local-only credentials and TLS files

From the `Etapa 3/OpenSpec` project root:

```powershell
python deployment\generate_local_config.py
```

The script creates `deployment/.env.local`, a random AES-256-GCM key, a separate audit HMAC key, a distinct administrative verification token, and a two-week self-signed development certificate for `localhost` and `127.0.0.1`. It refuses to overwrite existing local credentials or certificates. Values are not printed. `.env.local` and `deployment/certs/` are ignored by `deployment/.gitignore` and excluded from Docker build contexts. Keep the generated files outside source control. The keys are demonstration credentials and must not be reused for other data.

The safe `.env.example` contains names only. The application uses `SHIFT_BANK_DB`, `SHIFT_BANK_ENCRYPTION_KEYS`, `SHIFT_BANK_ACTIVE_KEY_VERSION`, `SHIFT_BANK_AUDIT_KEY`, and `SHIFT_BANK_AUDIT_ADMIN_TOKEN`. Startup fails before initializing the database when key material or the separate admin token is absent or invalid.

## Build and start

```powershell
docker compose --project-name shift-bank-e3-openspec-block4 --env-file deployment/.env.local -f deployment/compose.yaml build
docker compose --project-name shift-bank-e3-openspec-block4 --env-file deployment/.env.local -f deployment/compose.yaml up -d
docker compose --project-name shift-bank-e3-openspec-block4 --env-file deployment/.env.local -f deployment/compose.yaml ps
```

Use `https://localhost:18443/` for the application. `http://localhost:18080/` redirects to the HTTPS port. The certificate is self-signed; for manual browser testing, trust the local certificate explicitly or accept the browser's development warning. Automated checks should trust `deployment/certs/dev-cert.pem`, not disable TLS verification.

Compose creates the named persistent volume `shift-bank-e3-openspec-block4-data` and the isolated network `shift-bank-e3-openspec-block4-network` (172.29.240.0/24). The one-shot root `storage-init` service sets volume ownership; the long-running backend runs as UID/GID 10001. The frontend runtime uses the unprivileged Nginx image (UID 101). Only loopback ports are published; API requests pass through Nginx, which forwards `X-Forwarded-Proto` from the TLS connection. The backend trusts only Nginx's fixed network address.

Backend readiness checks SQLite, encryption-key availability, audit-key availability, the separate admin credential, and audit-chain verification. Nginx readiness checks the TLS frontend-to-backend path using the mounted certificate. Liveness and readiness endpoints return only a status field.

## Stop and preserve data

```powershell
docker compose --project-name shift-bank-e3-openspec-block4 --env-file deployment/.env.local -f deployment/compose.yaml down
```

This removes only this project's containers and network; the named data volume remains. Do not pass `--volumes` or `-v` when preserving local synthetic data. To restart, use the same project name, env file, certificate, and volume. Back up externally provisioned keys separately before moving or recovering a persistent database.
