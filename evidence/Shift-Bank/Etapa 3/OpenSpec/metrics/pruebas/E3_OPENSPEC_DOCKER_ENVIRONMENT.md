# Shift Bank E3 OpenSpec — Docker Environment

Captured for deployment project shift-bank-e3-openspec-block4 on 2026-11-16.

## Host and engine

- Docker CLI: 29.9.3 (build 5457199).
- Docker Compose: v5.7.0.
- Docker engine: Linux, x86_64; 12 CPUs; 42,000,900,096 bytes reported memory.
- Project uses locally built images and an isolated bridge network. No cloud service or remote banking integration is used.
- Before starting, existing Docker containers, networks and volumes were inspected. The existing SonarQube and other unrelated project resources were not modified or removed.

## Isolated resources

- Compose project: shift-bank-e3-openspec-block4.
- Network: shift-bank-e3-openspec-block4-network, 172.29.240.0/24.
- Persistent synthetic-data volume: shift-bank-e3-openspec-block4-data.
- Backend image: shift-bank-e3-openspec-backend:local.
- Frontend image: shift-bank-e3-openspec-frontend:local.
- Host listener bindings: 127.0.0.1:18080 (redirect) and 127.0.0.1:18443 (HTTPS).
- Backend port 8000 is only exposed inside the Compose network, not published to the host.
- Final database: /var/lib/shift-bank/bank-final.db.

The project uses one backend container, one Uvicorn process, and a one-shot storage ownership initializer. Nginx is the only published service. The deployment acceptance records show both application healthchecks healthy and demonstrate two backend restarts.

## Secret and certificate handling

Local test values are generated outside image layers by deployment/generate_local_config.py. deployment/.env.local, deployment/certs/, PEM and key files are ignored by version control and excluded from the Docker build context. The local TLS private key is mounted at runtime only. No secret values or MFA codes were recorded in evidence. The safe deployment/.env.example contains variable names/default database path and blank key fields.

## Original environment records

- E3_OPENSPEC_BLOCK4_20261116T154405_compose-build.log
- E3_OPENSPEC_BLOCK4_20261116T154439_compose-start.log
- E3_OPENSPEC_BLOCK4_20261116T154539_nginx-correction.log
- E3_OPENSPEC_BLOCK4_FINAL_RUNTIME_20261116T211350Z.txt (final service, runtime user, health and SQLite file metadata)
- E3_OPENSPEC_DEPLOYMENT_ACCEPTANCE.json (machine-readable actual acceptance and timestamps)
- E3_OPENSPEC_BLOCK4_HTTPS_RECORDS.json (actual request/check records)
