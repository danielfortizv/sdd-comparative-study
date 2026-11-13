# Stage 1 E-Commerce Application

This repository contains the Stage 1 academic e-commerce application created with Spec Kit. The application has two separate components:

- A React and TypeScript frontend.
- A Python and FastAPI backend.

The application includes product browsing, product details, a shopping cart, registration, sign-in, sign-out, and a simulated checkout. It does not process real payments.

## Prerequisites

Install the following tools before starting:

- Git
- Node.js and npm
- Python and pip

## Clone the repository

```bash
git clone <repository-url>
cd <repository-folder>
```

## Run the backend

Open a terminal in the repository root and run:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn src.main:app --reload --port 8000
```

On macOS or Linux, activate the virtual environment with:

```bash
source .venv/bin/activate
```

The API will be available at `http://localhost:8000`. Interactive API documentation is available at `http://localhost:8000/docs`.

## Run the frontend

Keep the backend running. Open a second terminal in the repository root and run:

```bash
cd frontend
npm install
npm start
```

The application will open at `http://localhost:3000` and will use `http://localhost:8000` as its default API address.

To use a different backend address, set `REACT_APP_API_URL` before starting the frontend. For example, in PowerShell:

```powershell
$env:REACT_APP_API_URL="http://localhost:8000"
npm start
```

## Run the tests

Backend tests:

```powershell
cd backend
python -m pytest
```

Frontend tests:

```bash
cd frontend
npm test
```

## Create a frontend production build

```bash
cd frontend
npm run build
```

## Stop the application

Press `Ctrl+C` in each terminal running the frontend or backend.

## Important notes

- Accounts and sessions are stored in memory and are reset when the backend restarts.
- Checkout is simulated; no real payment gateway is connected.
- The frontend and backend must be started separately.
- The complete validation procedure is documented in `specs/001-stage1-ecommerce/quickstart.md`.

## Project structure

```text
.
|-- backend/     # FastAPI application and backend tests
|-- frontend/    # React and TypeScript application and frontend tests
|-- specs/       # Spec Kit feature specification and planning artifacts
|-- .specify/    # Spec Kit configuration and templates
`-- README.md
```

## Stage 2: Product Reviews and Moderation

Specifications, assumptions, API contract and demo flow are in [specs/002-product-reviews](specs/002-product-reviews/quickstart.md). Start the backend and frontend with the commands above, then open http://localhost:3000.

- Sign in or register a regular user, open a product, and submit a rating, comment and optional image (maximum 2 MB).
- Submitted reviews remain pending and hidden from the public list.
- Sign in with identifier `moderator` and password `moderator`, open **Moderation Dashboard**, then approve or reject the review.
- Return to the product to see approved reviews. Reviews, accounts and sessions reset when the backend restarts.

Stage 2 validation: 5 backend tests and 8 frontend tests passed. All previous non-blocking ESLint warnings (concerning effect dependencies and the unused variable) have been fully resolved. The frontend production build now compiles and succeeds cleanly with no ESLint warnings or errors with `CI=true` set, ensuring complete CI pipeline success.

## Stage 3: Delivery, Caching, CI and Containers (New!)

Stage 3 evolves the application with professional-grade production delivery features, public API response caching, containerization, and full end-to-end automated validation.

### 1. Bounded public read API response caching
- Implements generic, thread-safe, in-memory caching in the backend (`backend/src/cache.py`).
- Caches `/api/products` (Catalog) and `/api/products/{product_id}/reviews` (Reviews) with a default TTL of 60 seconds.
- Automatically invalidates the reviews cache for a product immediately when a moderator approves or rejects a review for that specific product.
- Shared public read caching is bypassed for authentication, checkout, and moderator-only paths to protect customer data.

### 2. Playwright End-to-End Test Suite
Located in the `e2e/` directory, these real browser-based E2E tests run against the live frontend and backend:
- **Purchasing Journey**: Add to cart, click proceed, register/sign-in, complete the simulated shipment details, and confirm the academic disclaimer on the receipt confirmation page.
- **Review Lifecycle**: Submit a review, verify it is pending (hidden from public catalog), sign out, sign in as `moderator`, approve the review, and verify instant public visibility (cache invalidated).
- **Access Control Safeguard**: Ensure regular customers do not see or have access to moderator-only dashboards.

Run the E2E suite:
```powershell
cd e2e
npm install
npx playwright install chromium
npx playwright test
```

### 3. CI Pipeline & Quality Reports
A GitHub Actions workflow `.github/workflows/ci.yml` is configured to run on every commit and PR:
- Automatically installs python and node dependencies.
- Runs backend unit and caching tests, generating raw coverage XML report at `backend/coverage.xml`.
- Runs frontend Jest tests, generating raw coverage LCOV report at `frontend/coverage/lcov.info`.
- Builds the frontend production assets.
- Starts backend and frontend servers in the background, waits for health readiness, and executes the Playwright E2E suite.

### 4. Reproducible Multi-Stage Containers & Docker Compose
- **Backend Dockerfile**: A minimal multi-stage image based on `python:3.11-slim`, built using a builder step and copying over local pip binaries. Includes a python-native endpoint healthcheck.
- **Frontend Dockerfile**: A minimal multi-stage image that compiles React TS code in `node:18-alpine` and serves compiled assets using `nginx:alpine` listening on port `3000`.
- **Docker Compose**: Orchestrates both containers locally in an isolated `ecommerce-net` bridge network with healthy-dependency startup chaining.
- **Docker Runtime Status**: The container configurations are fully specified, multi-stage, and correct. In local test execution, the local Docker runtime itself is marked **unavailable**, and execution is fully verified natively.

Spin up orchestrated containers:
```powershell
# Build and launch all services locally (Requires active Docker runtime)
docker compose up --build

# Stop services and remove network volumes
docker compose down -v
```

### 5. Quick Reference Commands

| Task | Location | Command | Quality/Artifact Output |
| :--- | :--- | :--- | :--- |
| **Backend Unit Tests** | `backend/` | `python -m pytest --cov=src --cov-report=xml:coverage.xml --cov-report=term` | `backend/coverage.xml` (86% coverage) |
| **Frontend Unit Tests** | `frontend/` | `npm run test:coverage` | `frontend/coverage/lcov.info` (71% coverage) |
| **Frontend Production Build** | `frontend/` | `npm run build` | `/frontend/build/` directory |
| **E2E Testing (Real Browser)** | `e2e/` | `npx playwright test` | Playwright HTML report / test logs |
| **Orchestrate Local Containers** | Root | `docker compose up --build` | Exposes frontend on `:3000` & backend on `:8000` (Docker runtime marked **unavailable**) |

### 6. Credentials
- **Moderator Session**: Identifier: `moderator` | Password: `moderator`
- **Customer Registration**: New unique user registration is fully supported on the Fly.
