# E-Commerce Demo — Stage 4: Distributed Microservices & Event-Driven Architecture (Option A)

This repository contains a decoupled, responsive e-commerce web application migrated from a monolithic backend to independently running microservices with real RabbitMQ business events.

Stage 4 Option A evolves the application by introducing a distributed architecture with explicit state ownership, independent database isolation, transactional outbox publishing with publisher confirmations, idempotent event ingestion, and a thin HTTP routing gateway.

---

## 🔑 Demo Moderator Credentials

To test the review moderation workflow:
- **Username**: `moderator`
- **Password**: `moderator`

---

## 🏗️ Distributed Architecture & State Isolation

The backend is split into four independently startable FastAPI services:
1. **Gateway Service (Port 18400)**: Single HTTP client routing interface that proxies frontend calls to appropriate microservices.
2. **Identity Service (Port 18401)**: Owns `identity.db` (SQLite). Manages standard user/moderator accounts, session validation, and serves internal token verification (`/api/internal/verify-token`) for secure, non-spoofable auth.
3. **Commerce Service (Port 18402)**: Owns `commerce.db` (SQLite). Holds the product catalog, handles simulated checkout logic, stores the **public approved reviews projection**, and invalidates catalog caching.
4. **Reviews Service (Port 18403)**: Owns `reviews.db` (SQLite). Manages review submission, pending queues, moderation dashboards, and transactionally stages outbound events in an SQLite `outbox` table.

---

## ⚡ Event-Driven Flow (RabbitMQ)

The system utilizes a real RabbitMQ AMQP broker to propagate review approved events from the Reviews Service to the Commerce Service:
- **Exchange**: `stage4.tessl.exchange` (type: `direct`, durable)
- **Queue**: `commerce.review_projection_queue` (durable)
- **Routing Key**: `review.approved`

### 📤 Transactional Outbox Pattern
When a moderator approves a review:
1. The Reviews Service starts a database transaction in `reviews.db`.
2. It updates the review's status to `"approved"`.
3. It writes a structured JSON event payload into the `outbox` table in the same transaction.
4. It commits the transaction.
5. A background daemon thread inside the Reviews Service continually polls the outbox, publishes pending events to RabbitMQ with **Publisher Confirmations** enabled (`channel.confirm_delivery()`), and marks them as `processed = 1` once acknowledged by the broker.

### 📥 Idempotent Ingestion & Invalidation
1. The Commerce Service consumer listens to `commerce.review_projection_queue` on RabbitMQ.
2. Upon receiving a message, it verifies if `payload.review_id` is already present in its local `public_reviews` table.
3. If not present, it inserts the review into the projection table (idempotent design).
4. It invalidates its local reviews cache (`reviews:<product_id>`) in all cases to guarantee eventual consistency.
5. It manually acknowledges (ACK) the message to RabbitMQ.

---

## 🚀 Running the Application Locally

You can launch, check readiness, and cleanly terminate the entire local microservices stack using simple PowerShell scripts.

### 1. Start all Services
Run from the repository root:
```powershell
.\Start-Services.ps1
```
This script will delete previous local database files, start the 4 Python services and the frontend development server (on port `18500`), run deterministic readiness port-checking, and report successful startup.

### 2. Stop all Services
Run from the repository root:
```powershell
.\Stop-Services.ps1
```
This script will read the recorded process IDs (PIDs) from `services-pids.json`, cleanly stop each process, and run a fallback cleanup on the ports (`18400-18403`, `18500`) to prevent orphaned services.

---

## 🧪 Verification & Testing Suites

### 1. Pytest Unit Tests
Runs the backend tests asserting cache invalidation, authorization, registration, and simulation checks against the SQLite databases:
```powershell
python -m pytest backend/test_api.py -v --cov=backend/app --cov-report=xml:backend/coverage.xml
```

### 2. Distributed Integration Suite
Verifies standard user registration, catalog retrieving, pending review submissions, access denial, moderator approval, event propagation, eventual consistency, duplicate delivery, consumer idempotency, and simulated checkouts against the live distributed stack:
```powershell
python backend/test_distributed.py
```

### 3. Frontend Vitest Tests
Runs frontend React math and cart logic tests:
```powershell
cd frontend
npm run test
```

### 4. Playwright End-to-End Tests
Executes E2E browser tests verifying access control, purchasing journeys, and moderation lifecycles:
```powershell
cd frontend
npx playwright test
```

---

## ⚙️ Continuous Integration (CI)

Our comprehensive local CI pipeline orchestrates dependencies installation, Pytest tests, Vitest tests, the production frontend build, live microservices stack orchestration, E2E Playwright validation, and auto-cleanup:
```powershell
.\run-ci.ps1
```
The exact same automated steps are verified on every code push or PR via GitHub Actions in `.github/workflows/ci.yml`.
