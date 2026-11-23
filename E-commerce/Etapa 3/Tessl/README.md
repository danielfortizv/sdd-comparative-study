# E-Commerce Demo — Stage 3: Architecture & Automated Delivery Verification

This repository contains a decoupled, responsive e-commerce web application featuring a Python (FastAPI) backend and a React (TypeScript + Vite) frontend.

Stage 3 evolves the application by introducing automated E2E tests, a continuous integration pipeline, multi-stage Docker builds with local Compose orchestration, bounded public API response caching with invalidation, and standard coverage collection outputs.

---

## 🔑 Demo Moderator Credentials

To test the review moderation workflow:
- **Username**: `moderator`
- **Password**: `moderator`

---

## 🚀 Getting Started (Local Development)

### 1. Run the Backend (FastAPI)
Open a terminal in the `backend` folder:
```powershell
cd backend
python -m venv .venv
# Windows activation:
.\.venv\Scripts\Activate.ps1
# macOS/Linux activation:
source .venv/bin/activate

python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend API will be available at `http://127.0.0.1:8000` and Swagger docs at `http://127.0.0.1:8000/docs`.

### 2. Run the Frontend (React + TS)
Open a second terminal in the `frontend` folder:
```powershell
cd frontend
npm install
npm run dev
```
Open your browser at `http://localhost:3000` to interact with the application.

---

## 🐳 Docker Orchestration

Both frontend and backend are containerized with multi-stage Dockerfiles. To spin them up with isolated container networking and an automated backend readiness check, run from the repository root:

```powershell
docker-compose up --build
```
- **Backend service**: exposes port `8000`.
- **Frontend service**: exposes port `3000`.
- **Readiness Check**: The frontend container will only spin up and serve traffic once the backend health check (`GET /api/products` is responsive) returns successfully.

> **⚠️ Docker-Not-Installed Limitation:** If Docker or Docker Desktop is not installed on your system, container orchestration commands will fail. In this scenario, you must run and test the application directly on your local machine using the manual steps below or by running the comprehensive PowerShell CI pipeline (`.\run-ci.ps1`).

---

## 🧪 Verification & Testing Commands

We have structured tests to verify correctness across all layers of the application.

### 1. Backend Pytest Suite & Coverage
Runs backend unit, integration, caching, and auth tests, and compiles coverage XML:
```powershell
# Run from repository root
python -m pytest backend/test_api.py --cov=backend --cov-report=xml:backend/coverage.xml
```
*Generates coverage report at `backend/coverage.xml`.*

**Actual Pytest Cases executed (`backend/test_api.py`):**
- `test_get_products_and_caching`: Verifies product retrieval and bounded in-memory response cache (60s TTL), asserting subsequent requests hit the cache.
- `test_user_registration_and_login`: Verifies user registration with validation error handling, password hashing, and session login/logout endpoints.
- `test_checkout_validation_and_simulation`: Verifies checkout endpoint validation (such as denying empty checkout payloads) and successful checkout simulation.
- `test_reviews_submission_and_moderation_flow`: Verifies review submission, moderator auth-only queues, moderation action (Approve/Reject) effects, and immediate cache invalidation for updated product reviews.

### 2. Frontend Vitest Suite & Coverage
Runs frontend math and cart logic tests, and compiles LCOV coverage:
```powershell
# Run from frontend folder
cd frontend
npm run test
```
*Generates coverage report at `frontend/coverage/lcov.info`.*

**Actual Vitest Cases executed (`frontend/src/__tests__/cart_math.test.ts`):**
- `should calculate the total purchase amount correctly`: Verifies item quantities, pricing totals, and rounding logic.
- `should return 0 for an empty cart`: Verifies empty-state cart boundary conditions.

### 3. Playwright End-to-End Tests
Executes the Playwright suite verifying the purchasing journey, reviews & moderation lifecycle, and access-control checks against live servers:
```powershell
# Run from frontend folder
cd frontend
npx playwright test
```

**Actual Playwright E2E Scenarios executed (`frontend/e2e/`):**
- `purchasing-journey.spec.ts` (`Complete simulated purchasing journey`): Verifies product catalog interaction, cart additions, checkout navigation guards redirection to dynamic user registration, checkout summary consistency, and state-reset post-confirmation.
- `reviews-moderation.spec.ts` (`Complete reviews submission, moderation, and visibility lifecycle`): Verifies standard reviews list viewing, reviews submission guard, review creation (pending state is initially hidden from visitor views), moderator approval, and immediate public visibility update.
- `access-control.spec.ts` (`Regular customer denied access to moderation dashboard and APIs`): Verifies standard logged-in customer is restricted from accessing the moderation dashboard UI component and receives a 403 Forbidden on restricted endpoints.

---

## ⚙️ Continuous Integration (CI)

We provide two ready-to-use CI pipeline environments:

### 1. Local PowerShell CI script (`run-ci.ps1`)
You can execute the entire verification pipeline locally on Windows. It will install all dependencies, execute backend/frontend tests and coverage compilation, perform a production compilation of the React frontend, start background servers, trigger the Playwright E2E test suite, and automatically clean up all background tasks:
```powershell
# Run from repository root
.\run-ci.ps1
```

### 2. Remote GitHub Actions Workflow
Every push or pull request to `main` / `master` automatically runs the CI pipeline inside `.github/workflows/ci.yml` on a Linux runner.

---

## ⚡ Bounded API Response Caching & Invalidation Design

To handle catalog traffic efficiently, we implemented a bounded in-memory response cache:
1. **Target Endpoints**: `GET /api/products` and `GET /api/products/{id}/reviews`.
2. **Caching Rules**: Expiry is bounded with a default Time-To-Live (TTL) of 60 seconds.
3. **Cache Invalidation**: Whenever a product review is submitted (`POST /api/products/{id}/reviews`) or has its status updated by a moderator (`POST /api/moderation/reviews/{id}/status`), the cache for that product's reviews (`reviews:{id}`) is immediately invalidated. This ensures approved reviews are visible instantly while keeping standard catalog requests blazingly fast.
4. **Safety Restrictions**: Private/sensitive routes (like `checkout`, `login`, `register`, and the moderator queues) bypass caching entirely to prevent data leakage.
