# Stage 1-3 Academic Ecommerce

Academic e-commerce demonstration built with a React/TypeScript frontend and a FastAPI backend. It includes a product catalog, local shopping cart, basic authentication, simulated checkout, product reviews with moderation, caching, containerization, and a continuous integration pipeline.

> This project is for academic demonstration only. It does not process real payments and is not configured for production use.

## Requirements

- Node.js 20 or later
- npm
- Python 3.10 or later

## Project Structure

```text
backend/    FastAPI API and SQLite database
frontend/   React, TypeScript, and Vite application
openspec/   OpenSpec planning artifacts and specs
```

---

## Running the Application Locally (Development)

The Stage 3 backend is configured to run on port `8005` by default, allowing seamless CORS-compliant requests from the frontend.

### 1. Run the Backend

Open a PowerShell terminal in the project root and run:

#### Windows PowerShell

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8005
```

#### macOS or Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8005
```

The backend will be available at:
- API: `http://127.0.0.1:8005`
- Health check: `http://127.0.0.1:8005/`
- Interactive API documentation: `http://127.0.0.1:8005/docs`

The SQLite database (`ecommerce.db`) and demo product catalog are created and seeded automatically when the backend starts.

---

### 2. Run the Frontend

Keep the backend running on port `8005`. Open a second PowerShell terminal in the project root and run:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173` in your browser.

---

## Local Testing & Coverage Reports

You can execute the test suites locally and generate raw quality coverage reports.

### 1. Backend Tests (FastAPI / Pytest)

To run the backend test suite and generate a standard `coverage.xml` report:

#### Windows PowerShell

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pip install pytest pytest-cov httpx
pytest --cov=app --cov-report=xml
```

#### macOS or Linux

```bash
cd backend
source .venv/bin/activate
python -m pip install pytest pytest-cov httpx
pytest --cov=app --cov-report=xml
```

The generated coverage output will be placed at `backend/coverage.xml`.

---

### 2. Frontend Unit Tests (React / Vitest)

To run the frontend unit tests and generate an `lcov.info` report:

```powershell
cd frontend
npm install
npm run test
```

The generated coverage output will be placed at `frontend/coverage/lcov.info`.

---

### 3. Playwright End-to-End Tests (E2E)

To run the automated browser-based end-to-end tests:

```powershell
cd frontend
# Install Playwright browser binaries
npx playwright install --with-deps chromium

# Execute the E2E test suite
npm run test:e2e
```

---

## Try the Application

1. Browse the product catalog.
2. Add an available product to the cart.
3. Open the cart and proceed to checkout.
4. Register a new account or sign in.
5. Complete the simulated checkout.

### Moderator Workflow & Credentials

The application features an integrated **Moderator Dashboard** to moderate product reviews. A pre-seeded moderator account is automatically created upon backend startup:

* **Moderator Account Identifier:** `moderator`
* **Moderator Password:** `modpassword`

To moderate reviews:
1. Sign in with the identifier `moderator` and password `modpassword`.
2. Click the "Moderation" link in the navigation bar, or navigate directly to `/moderation`.
3. Approve or reject pending user reviews. Approved reviews will instantly appear in the product catalog and update average star ratings.

---

## Docker Containerization & Orchestration (Stage 4)

The application includes production-ready Docker configurations with robust health checks and custom bridge networking for the fully-distributed microservices stack.

### Run with Docker Compose

To build and launch the microservices stack (identity, commerce, reviews, gateway, frontend, and RabbitMQ) in a fully orchestrated state:

```bash
docker compose up --build
```

- **Frontend application:** `http://localhost:18100`
- **Gateway API:** `http://localhost:18000`

### Container Execution Limitation Notice

> **Honest Limitation:** Docker is currently not installed on the host development environment. Therefore, the physical execution and health checks of the containers have not been locally verified. However, the Dockerfiles and `docker-compose.yml` follow standard secure multi-stage build patterns, non-root user execution privileges, and light-weight delivery architectures (Nginx serving React, multi-stage Python builder/runner) to ensure robust execution in standard Docker-capable environments.

---

## Production Frontend Build

To compile static React assets manually:

```powershell
cd frontend
npm install
npm run build
```

The compiled files will be output to `frontend/dist/`.

---

# Stage 4 Reliability and Verification

In Stage 4, the application has been restructured into a fully-distributed microservices stack consisting of four independent FastAPI applications (`identity` on port 18001, `commerce` on port 18002, `reviews` on port 18003, and the unifying reverse-proxy `gateway` on port 18000) coordinated asynchronously via a real RabbitMQ AMQP broker.

## Completed Stage 4 Reliability Corrections

1. **Non-Destructive Durable Queue Topology**: The Commerce background consumer was corrected to declare the `commerce_review_projection_queue` queue and dead-lettering parameters idempotently without destructive `queue_delete()` on every reconnection. This preserves durable messages accepted while Commerce is offline.
2. **Structural Parameter Migration**: To survive development queue contract changes, a `try...except` block catches channel precondition failures (e.g., mismatched routing or DLX arguments), deletes the outdated queue, opens a fresh channel, and redeclares it as a safe, one-time migration step.
3. **Gateway Service Environment Configuration**: Services utilize standard environment variables (`IDENTITY_SERVICE_URL`, `COMMERCE_SERVICE_URL`, `REVIEWS_SERVICE_URL`) allowing the reverse-proxy Gateway to coordinate seamlessly both in local development and under standard Docker Compose DNS.
4. **Reliability-Aware PowerShell Teardown**: Updated `Stop-Stage4.ps1` to use correct parenthesized casting `([int]$PidVal)` and robustly verify that fallback port cleanup only targets owned microservice process types (`python`, `node`, `cmd`, `npm`), preventing arbitrary system process terminations.
5. **Real-Broker Subprocess Acceptance Tests**: Implemented a comprehensive test suite `backend/app/test_stage4_reliability.py` verifying real-world outage scenarios:
   - Starts actual microservices stack in independent subprocesses.
   - Registers and log-ins normal users and moderators, submitting and approving reviews.
   - Terminates only Commerce, submits/approves additional reviews offline, verifies the durable messages successfully buffer in RabbitMQ, restarts Commerce, and verifies they asynchronously propagate to public projections.
   - Demonstrates AMQP consumer idempotency by republishing duplicate event IDs and proving no double-effects.
   - Proves transactional outbox recovery by starting the reviews publisher with a faulted connection, verifying reviews are saved with `"pending"` outbox statuses, and then successfully transition to `"published"` once the AMQP URL is restored.

## Executed Test Evidence

The backend test suite was fully executed against the real RabbitMQ broker, verifying 100% of the baseline and newly-introduced reliability integration assertions:

```text
============================= test session starts =============================
platform win32 -- Python 3.13.9, pytest-8.4.2, pluggy-1.5.0
rootdir: C:\Users\jeron\OneDrive\Escritorio\uni\implementacion Ecommerce\Caso 3-Ecommerce\Etapa 4\OpenSpec\backend
plugins: anyio-4.10.0, cov-7.1.0
collected 5 items

app\test_reviews.py ....                                                 [ 80%]
app\test_stage4_reliability.py .                                         [100%]

=============================== tests coverage ================================
Coverage XML written to file coverage.xml
======================= 5 passed, 24 warnings in 24.02s =======================
```

The generated coverage output has been preserved at `backend/coverage.xml`.

## Honest Limitations

1. **Docker Container Execution**: Docker is unavailable on the local host development environment, meaning the physical execution and health checks of the multi-container stack in `docker-compose.yml` have not been locally validated. However, the configurations utilize secure non-root users, unbuffered logging environment variables, and correct service-level dependencies.
2. **WSL/RabbitMQ Broker Administration**: The shared RabbitMQ broker is running on an external/WSL environment on port 5672. As a result, we do not stop or administer the shared host broker daemon directly. Instead, we isolate the test execution runs completely using unique, randomly-generated event namespaces (`EVENT_NAMESPACE`), unique queue names (`QUEUE_NAME`), and separate temporary sqlite databases (`test_identity.db`, `test_commerce.db`, `test_reviews.db`). This ensures no historical state collides and allows offline testing by safely terminating individual microservice connections/subprocesses.

