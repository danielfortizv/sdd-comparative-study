# Shift Bank E3 OpenSpec — Block 4 Deployment Evidence

Run ID: DEPLOYMENT_20261116T211350Z  
Project: shift-bank-e3-openspec-block4  
Final acceptance: PASS, 50/50 checks  
UTC interval: 2026-11-16T21:12:02.425Z to 2026-11-16T21:13:50.632Z

## Implemented files

Added deployment assets: deployment/backend.Dockerfile, deployment/frontend.Dockerfile, deployment/nginx.conf, deployment/compose.yaml, deployment/.env.example, deployment/.gitignore, deployment/generate_local_config.py, deployment/verify_deployment.py, deployment/README.md, and .dockerignore.

Updated backend/encryption.py and backend/audit.py to expose key-configuration validation; backend/main.py to fail closed at startup and provide safe live/readiness health endpoints; backend/tests/test_api.py to provide/restores test key settings for lifespan tests. The OpenSpec tasks file records the verified deployment tasks.

## Deployment and security behavior

Compose runs the existing FastAPI app as one Uvicorn process in a non-root UID 10001 container. The React/Vite production assets are built into an unprivileged Nginx UID 101 container. Nginx listens on loopback-published ports 127.0.0.1:18080 and 127.0.0.1:18443. HTTP requests redirect to HTTPS with the HTTPS port in Location. Nginx terminates TLS 1.2/1.3 and proxies API and health routes to the backend on a private Compose network. The backend has no published host port and trusts forwarded scheme only from the fixed Nginx network address.

Encryption, audit-integrity, and separate audit-admin credentials are generated locally with deployment/generate_local_config.py into ignored deployment/.env.local. The development certificate and private key are mounted as Compose secrets from ignored deployment/certs files. The generator does not print material and refuses to overwrite existing local files. .dockerignore excludes local secrets/certificates; image config inspection found none of the three secret environment variables. No credentials, private keys, or real data were added to evidence.

A new named volume, shift-bank-e3-openspec-block4-data, holds isolated synthetic SQLite data. The final verified database path is /var/lib/shift-bank/bank-final.db. A one-shot root storage-init container sets volume ownership; the application stays non-root and the database/directory are owned by UID/GID 10001. Nginx is UID/GID 101. Ports bind to loopback only. Compose restricts the backend service to one named container and one Uvicorn process, so the scheduler is not scaled into multiple owners.

Startup probes against the built application image with no network confirmed safe failure when the encryption key, audit key, or admin credential is absent. Normal startup and readiness succeeded with locally provisioned values. Readiness checks the database, key configuration and audit-chain verification and returns only safe status.

## Live acceptance

The final acceptance JSON and per-request HTTPS records are machine-readable. All 50 checks passed, including:
- HTTPS frontend/assets; HTTP redirect; live/readiness; banking API routing and malformed/unauthorized request rejection.
- Balance/history reads and a real internal transfer with conserved balances.
- HTTPS beneficiary creation and authorized server-side decryption.
- MFA-protected ACH: pending and invalid MFA caused no debit; valid MFA authorized settlement; settlement and one debit persisted.
- Administrative audit verification denied without authorization and valid with the externally supplied admin credential.
- Sensitive persisted fields were ciphertext; audit chain remained valid after two backend restarts.
- Balances, history and ACH settlement survived restart. A synthetic due recurring schedule recovered after restart without an occurrence or duplicate recovery/financial effect.
- Backend/frontend healthchecks healthy; backend not host-published; single scheduler service could not be scaled; persistent volume exists; non-root identities and writable volume were confirmed.

Acceptance cases: AC-01 PASS (deployed inherited banking workflows); AC-12 PASS (Compose, TLS, redirect, reverse proxy, endpoints, health, secrets); AC-13 PASS (volume, non-root, encryption/audit persistence, restart and scheduler recovery); AC-14 PASS (full backend/frontend regressions, production build, strict OpenSpec validation). Deployment test details are in E3_OPENSPEC_DEPLOYMENT_ACCEPTANCE.json and E3_OPENSPEC_BLOCK4_HTTPS_RECORDS.json.

## Failures and corrections preserved

- Initial Nginx startup logged that its optional IPv6 entrypoint helper could not edit the read-only config. Removed that unused helper from the frontend image and rebuilt; subsequent startup had healthy checks.
- Attempt 01 exposed verifier mistakes (history endpoint expectation, healthcheck timing) and a Compose run probe static-IP conflict. The runner now compares persisted history count and waits for both healthchecks; missing-key probes use docker run with network=none.
- Attempt 02 exposed a missing explicit local DB-path fixture entry. Attempt 03 exposed a boolean-versus-count verifier assertion. Attempt 04 passed all checks, but final config review found a malformed local-only path line created during setup. The ignored local env line was normalized, and the final clean path acceptance run passed 50/50. Each prior output remains in its ATTEMPT-specific files.

## Commands and verification

Compose project commands used:
- docker compose --project-name shift-bank-e3-openspec-block4 --env-file deployment/.env.local -f deployment/compose.yaml build
- docker compose --project-name shift-bank-e3-openspec-block4 --env-file deployment/.env.local -f deployment/compose.yaml up -d
- python deployment/verify_deployment.py --output ..\_experiment_logs\OpenSpec\pruebas\E3_OPENSPEC_DEPLOYMENT_ACCEPTANCE.json --http-log ..\_experiment_logs\OpenSpec\pruebas\E3_OPENSPEC_BLOCK4_HTTPS_RECORDS.json
- python -m unittest discover -s tests -v (backend): 53 passed.
- npm.cmd --prefix frontend test: 8 passed.
- npm.cmd --prefix frontend run build: TypeScript and Vite production build passed.
- openspec.cmd validate --all --strict: 6 passed, 0 failed.

Original build/start/correction logs: E3_OPENSPEC_BLOCK4_20261116T154405_compose-build.log, E3_OPENSPEC_BLOCK4_20261116T154439_compose-start.log, E3_OPENSPEC_BLOCK4_20261116T154539_nginx-correction.log. Raw failed attempts and HTTPS records are retained as E3_OPENSPEC_DEPLOYMENT_ATTEMPT01_*, ATTEMPT02_*, ATTEMPT03_*, and ATTEMPT04_PASS_*.

The preserved Locust RUN_01 remains at ../locust/E3_OPENSPEC_LOCUST_RUN_01.json with its raw CSVs. It was not rerun and is not represented as Docker deployment performance.

## Limitations and next phase

This is a loopback-only local development deployment with a self-signed, short-lived certificate and local externally provisioned test secrets, not a production banking environment. An initial image build reported three npm audit advisories (one moderate, two high); dependencies were not changed in this block. Docker resources belonging to other projects were left untouched. SonarQube and final experimental closure have not started.
