---
name: Containerized Local Deployment
description: Production-like local deployment using Docker Compose with separate FastAPI and React/Nginx containers, reverse proxy, persistent volume, HTTPS/TLS, health checks, single scheduler instance, and Event Sourcing/CQRS runtime integrity
targets:
  - ../docker-compose.yml
  - ../backend/Dockerfile
  - ../frontend/Dockerfile
  - ../nginx/nginx.conf
---

# Containerized Local Deployment

Defines the multi-container architecture and orchestration specifications for local deployment using Docker Compose. The environment isolates the FastAPI backend service and React frontend behind an Nginx reverse proxy with HTTPS/TLS termination, volume persistence for SQLite, health monitoring, guaranteed single-instance background scheduling, and protection of administrative endpoints.

Governed by Researcher Decision D-12 and SEED-4 Items 3, 4, 5, and 6.

## Architecture Contract

```yaml
# Expected Service Topology
services:
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=sqlite:////app/data/shift_bank.db
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - AUDIT_SECRET_KEY=${AUDIT_SECRET_KEY}
      - ADMIN_SECRET_KEY=${ADMIN_SECRET_KEY}
      - RUN_SCHEDULER=true
    volumes:
      - shiftbank_data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 10s
      timeout: 5s
      retries: 3
  
  frontend:
    build: ./frontend
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      backend:
        condition: service_healthy
    volumes:
      - ./nginx/certs:/etc/nginx/certs:ro

volumes:
  shiftbank_data:
```

## Multi-Container Composition & Services

- Docker Compose defines two primary application services: `backend` (FastAPI) and `frontend` (React + Nginx reverse proxy). [INHERITED]
  `[@test] ../backend/tests/test_deployment_config.py`
- Backend runs Uvicorn ASGI server exposed internally to the Docker network on port 8000 (not directly bound to public host ports). [INHERITED]
  `[@test] ../backend/tests/test_deployment_config.py`
- Frontend multi-stage Docker build compiles the Vite/React application and packages static artifacts into an Nginx web server container. [INHERITED]
  `[@test] ../backend/tests/test_deployment_config.py`
- Nginx acts as the unified ingress reverse proxy:
  - Directs `/api/*` and `/docs` requests to the internal backend service (`http://backend:8000`).
  - Serves compiled static frontend assets with SPA fallback routing for client-side navigation (`try_files $uri /index.html`). [INHERITED]
  `[@test] ../backend/tests/test_deployment_config.py`

## HTTPS and TLS Configuration

- Reverse proxy terminates TLS on port 443 using local SSL/TLS certificates mounted from `./nginx/certs`. [INHERITED]
  `[@test] ../backend/tests/test_deployment_config.py`
- Plain HTTP traffic on port 80 automatically issues an HTTP 301 Permanent Redirect to `https://$host$request_uri`. [INHERITED]
  `[@test] ../backend/tests/test_deployment_config.py`
- TLS configuration mandates secure protocols (TLSv1.2, TLSv1.3) and modern cipher suites. [INHERITED]
  `[@test] ../backend/tests/test_deployment_config.py`

## Persistent Storage & Event Store Durability

- SQLite database (`shift_bank.db`), `domain_events` table, projection tables, and audit ledger tables reside in named Docker volume (`shiftbank_data`) mounted at `/app/data/`. [MODIFIED D-12]
  `[@test] ../backend/tests/test_deployment_config.py`
- Data survives container stop, restart, teardown, and rebuild operations (`docker compose down && docker compose up`). [INHERITED D-12]
  `[@test] ../backend/tests/test_deployment_config.py`

## Environment Secrets Management

- Sensitive configuration values are injected via environment variables:
  - `ENCRYPTION_KEY`: 32-byte key used for AES-256-GCM encryption at rest.
  - `AUDIT_SECRET_KEY`: Signing key used for HMAC-SHA256 audit ledger signatures.
  - `ADMIN_SECRET_KEY`: Secret key protecting administrative endpoints from unauthorized access.
  - `DATABASE_URL`: Path pointing to the persistent SQLite database inside the volume.
  `[@test] ../backend/tests/test_deployment_config.py`
- No New Infrastructure Secrets: Stage 4 reuses the inherited secret keys; no new external broker tokens or required environment variables are introduced. [NEW D-12]
  `[@test] ../backend/tests/test_deployment_config.py`

## Health Monitoring & Startup Sequencing

- The backend container exposes a health check probe querying `GET /api/health` with 10-second intervals and 3-retry threshold. [INHERITED]
  `[@test] ../backend/tests/test_deployment_config.py`
- Startup Projection Checkpoint Verification: On startup, backend verifies that CQRS read projections are synchronized with the `domain_events` sequence. Missing or stale projections trigger safe automated rebuild before healthcheck reports healthy. If recovery fails, backend fails closed and refuses operations. [NEW D-06, D-12]
  `[@test] ../backend/tests/test_deployment_config.py`
- Frontend startup waits for backend health confirmation using `condition: service_healthy` before accepting incoming traffic. [INHERITED]
  `[@test] ../backend/tests/test_deployment_config.py`

## Single Scheduler Instance Guarantee

- To prevent race conditions, duplicate ACH settlements, and duplicate recurring transfer executions, the background scheduler runs strictly on a single instance controlled by `RUN_SCHEDULER="true"`. [INHERITED D-09, D-12]
  `[@test] ../backend/tests/test_deployment_config.py`

## Administrative Operations & Protection

- Ingress protection requires an administrative header (`X-Admin-Key`) validated against `ADMIN_SECRET_KEY`. Requests lacking this header are rejected with HTTP 403 Forbidden. [INHERITED]
  `[@test] ../backend/tests/test_deployment_config.py`
- Protected Projection Rebuild CLI: The projection rebuild routine established in D-06 runs as an on-demand local administrative CLI/service routine (`python -m backend.app.rebuild_projections`) within the backend container without exposing an unauthenticated public HTTP endpoint. [NEW D-06, D-12]
  `[@test] ../backend/tests/test_deployment_config.py`
