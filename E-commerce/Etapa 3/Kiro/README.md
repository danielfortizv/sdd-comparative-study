# E-Commerce Stage 1 + Stage 2 + Stage 3

This repository contains a demonstration e-commerce application generated for the SDD tools comparison. It consists of a React and TypeScript frontend and a Python and FastAPI backend.

**Stage 1** delivers the core purchasing journey: browse the catalog, manage a local cart, register or sign in, and complete a simulated checkout.

**Stage 2** adds **product reviews with images and moderation** on top of Stage 1, without changing the Stage 1 journey. A signed-in customer can submit a review (star rating, text, optional title, and up to three images) for a product; every review enters a moderation queue; a moderator approves or rejects it; and only approved reviews are shown publicly on the product together with an aggregate rating summary. See the native specification in `.kiro/specs/ecommerce-stage2/` (requirements, design, tasks) and the inherited Stage 1 spec in `.kiro/specs/ecommerce-stage1/`.

**Stage 3** adds **architecture and automated delivery verification** (Option A) on top of Stage 2, without changing any application behavior: real end-to-end (Playwright) tests against the running stack, a CI pipeline (install → test with coverage → build → E2E), reproducible multi-stage Docker builds with a one-command local orchestration, and bounded caching for the public catalog read endpoints. See the native specification in `.kiro/specs/ecommerce-stage3/` (requirements, design, tasks). The quickest way to run and verify Stage 3 is the [Stage 3 section below](#stage-3-e2e-tests-ci-containers-and-caching).

## Prerequisites

- Python 3.11 or later
- Node.js 18 or later
- npm

## Project structure

```text
backend/    FastAPI API, services, data access, and backend tests
frontend/   React application, client-side state, and frontend tests
.kiro/      Kiro specification artifacts
```

## Run the application

The backend and frontend must run in separate terminals.

### 1. Start the backend

Open a terminal in the repository root and run:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

On macOS or Linux, activate the virtual environment with:

```bash
source .venv/bin/activate
```

The backend will be available at:

- API: <http://localhost:8000>
- Health check: <http://localhost:8000/health>
- Interactive API documentation: <http://localhost:8000/docs>

### 2. Start the frontend

Open a second terminal in the repository root and run:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173> in a browser.

The frontend expects the backend to be running at `http://localhost:8000`.

## Run the tests

### Backend

With the backend virtual environment activated:

```powershell
cd backend
pytest
```

### Frontend

```powershell
cd frontend
npm test
```

## Build the frontend

To type-check the frontend and create a production build:

```powershell
cd frontend
npm run build
```

The generated production files will be placed in `frontend/dist`.

## Stage 2: reviews, images, and moderation

### How to try it

1. Start the backend and frontend as described above (two terminals). The backend seeds a demonstration moderator account automatically at startup.
2. In the browser, open a product's **View details** panel in the Catalog. The expanded panel shows the product's approved reviews, a rating summary, and — when you are signed in as a customer — a review submission form.
3. **Submit a review** as a customer: register or sign in on the **Account** view, then expand a product, choose a rating, write the review text (optionally a title), optionally attach up to three images, and submit. The review is created as `pending` and is not yet publicly visible.
4. **Moderate** the review: sign out, then sign in with the moderator credentials below and open the **Moderation** destination in the top navigation. The pending review appears in the queue with its product, rating, text, images, and author. Approve it to make it publicly visible (and counted in the rating summary) or reject it to keep it hidden.
5. Re-open the product's details as any visitor: approved reviews and the rating summary are now shown.

### Moderator demonstration credentials

A single built-in moderator account is seeded at backend startup so the moderation workflow can be demonstrated immediately:

| Field | Value |
| --- | --- |
| Identifier | `moderator` |
| Password | `moderator123` |

These are a local-demo convenience defined in `backend/app/services/moderator_seed.py`. Sign in with them on the Account view; the **Moderation** view then becomes usable. A regular customer account cannot access moderation.

### Stage 2 endpoints (added additively over the Stage 1 six)

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/products/{id}/reviews` | Approved reviews + rating summary for a product |
| `POST` | `/products/{id}/reviews` | Submit a review (active customer session required) |
| `GET` | `/reviews/images/{imageId}` | Serve a stored review image |
| `GET` | `/moderation/reviews` | Pending moderation queue (moderator session required) |
| `POST` | `/moderation/reviews/{reviewId}/approve` | Approve a pending review (moderator) |
| `POST` | `/moderation/reviews/{reviewId}/reject` | Reject a pending review (moderator) |

## Important implementation notes

- The catalog, account, and review data use an in-process demonstration store; nothing is persisted durably across backend restarts.
- Review **image bytes** are the only on-disk artifact: they are written to the git-ignored folder `backend/app/data/review_images/` and served through the backend. No external object storage, CDN, or paid service is used.
- Review images are submitted as base64-encoded data in the JSON request, validated (type allow-list JPEG/PNG/GIF/WebP, max 2 MB, up to 3 per review), and only then stored.
- Moderation states are `pending`, `approved`, and `rejected`; a decision is terminal. A customer may submit at most one review per product, and submitted reviews cannot be edited or deleted. These and other delegated decisions are documented as assumptions A1–A8 in `.kiro/specs/ecommerce-stage2/requirements.md`.
- The cart and session state are kept in frontend memory and are reset when the page is reloaded.
- Checkout is simulated. No real payment is processed and no order is persisted.
- All interface text, code, comments, and specifications are in English.

## Stage 3: E2E tests, CI, containers, and caching

Stage 3 is additive: the nine existing endpoints' request/response bodies are unchanged except for added cache/freshness response headers, and the frontend journeys and views are unchanged. The native Stage 3 spec lives in `.kiro/specs/ecommerce-stage3/`.

### Demo / moderator credentials

The seeded moderator account (used by the review-lifecycle E2E test and by manual moderation) is unchanged from Stage 2:

| Field | Value |
| --- | --- |
| Identifier | `moderator` |
| Password | `moderator123` |

### Exact startup commands (PowerShell)

Run the backend and frontend in two terminals from the repository root.

Backend (first terminal):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend (second terminal):

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The frontend calls the backend at `http://localhost:8000`.

### Exact testing / verification commands (PowerShell)

Backend tests with a raw coverage report (`backend/coverage.xml`, Cobertura):

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install coverage
coverage run -m pytest
coverage xml -o coverage.xml
```

Frontend unit/integration tests with a raw coverage report (`frontend/coverage/lcov.info`, LCOV):

```powershell
cd frontend
npm run test:coverage
```

Frontend production build (type-check + Vite build into `frontend/dist`):

```powershell
cd frontend
npm run build
```

Real end-to-end tests (Playwright boots the real backend and the production build, then drives Chromium). Run once to install the browser, then run the suite:

```powershell
cd frontend
npx playwright install chromium
npm run test:e2e
```

The E2E suite covers three journeys: the Stage 1 purchasing journey, the Stage 2 review lifecycle (submit → pending/hidden → moderator approval → public), and a moderation access-denied check for a regular customer. The Playwright config starts `uvicorn` from `backend/` (using `backend/.venv` when present) on port 8000 and `vite preview` on port 4173; if a server cannot start, the run fails loudly rather than passing against a dead stack.

### Bounded public API caching

- Only the two session-independent public catalog reads are cached: `GET /products` and `GET /products/{id}`.
- The cache is in-process and bounded by both a per-entry TTL and a maximum entry count. Defaults: TTL `30s` (`CATALOG_CACHE_TTL_SECONDS`, set `0` to disable), max entries `256` (`CATALOG_CACHE_MAX_ENTRIES`).
- Cached responses carry `X-Cache: HIT|MISS` and `Cache-Control: public, max-age=<ttl>`. Session-varying and authenticated responses — `GET /products/{id}/reviews` (it includes the caller's own review), `/auth/*`, and `/moderation/*` — are marked `Cache-Control: no-store` and are **never** shared-cached, so no per-user data can leak between callers.
- **Invalidation / freshness:** the review-listing endpoint is intentionally uncached, so a newly approved review is immediately publicly visible; a moderation approve/reject additionally calls a cache-invalidation hook. Stale catalog entries cannot outlive their TTL.

Example (observe the cache headers):

```powershell
# First call: X-Cache: MISS ; second call within the TTL: X-Cache: HIT
(Invoke-WebRequest http://localhost:8000/products -UseBasicParsing).Headers['X-Cache']
(Invoke-WebRequest http://localhost:8000/products -UseBasicParsing).Headers['X-Cache']
```

### Containers and one-command local orchestration

Reproducible multi-stage builds are provided: `backend/Dockerfile` (`python:3.11-slim` builder + slim runtime, uvicorn on container port 8000) and `frontend/Dockerfile` (`node:20-alpine` build stage → `nginx:1.27-alpine` serving the static build on container port 80). A single orchestration command starts both with a user-defined bridge network and a `/health` readiness healthcheck on the backend:

```powershell
docker compose up --build
```

This publishes the backend on host port 8000 and the frontend on host port 8080 (open <http://localhost:8080>). Because the backend is published on host 8000, the frontend's existing `http://localhost:8000` API base URL keeps working unchanged. No external or paid service is used and nothing is deployed.

> **Runtime note (honest limitation):** Docker was **not available** in the environment where this stage was validated (`docker` is not on PATH). The `Dockerfile`s, `nginx.conf`, and `docker-compose.yml` were validated by inspection and are exercised by the CI definition, but **a local container run was not executed and is not claimed.** Run `docker compose up --build` on a machine with Docker installed to start the containerized stack.

### Continuous integration

`.github/workflows/ci.yml` runs on push and pull request: it installs backend and frontend dependencies, runs the backend tests producing `coverage.xml`, runs the frontend unit tests producing `lcov.info`, builds the frontend, installs the Playwright browser, runs the E2E suite against the real stack, and uploads the coverage reports and the Playwright report as artifacts. It does **not** publish or deploy to any external infrastructure.

> **Coverage note:** the coverage reports (`backend/coverage.xml`, `frontend/coverage/lcov.info`) are produced for later quality analysis. No coverage target is prescribed and no unexecuted check is claimed as passed.
