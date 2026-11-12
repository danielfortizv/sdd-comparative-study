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

## Docker Containerization & Orchestration (Stage 3)

The application includes production-ready Docker configurations with robust health checks and custom bridge networking.

### Run with Docker Compose

To build and launch the backend and frontend in a fully orchestrated state:

```bash
docker compose up --build
```

- **Frontend application:** `http://localhost:5173`
- **Backend API:** `http://localhost:8005`

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
# Final Stage 3 Local Verification

The generated Playwright suite passed its complete purchasing, review submission, pending-hidden, moderation approval, public visibility, and access-denied journey against fresh real servers on ports 8005 and 5173. This final execution was performed by the experiment orchestrator using the unchanged native OpenSpec test, after the CLI encountered provider/shell execution interruptions. No application or test source was modified by that independent validation.

The final backend checks passed (2 tests), frontend unit checks passed (3 tests), and `backend/coverage.xml` and `frontend/coverage/lcov.info` were refreshed against the final source. Raw independent execution results are under `../Evaluacion/OpenSpec/*validation.txt`; `local-validation-metadata.json` records the E2E driver and timestamps. Docker execution and remote GitHub Actions execution remain unperformed.

