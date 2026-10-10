# E-Commerce Stage 1

This repository contains a demonstration e-commerce application generated for Stage 1 of the SDD tools comparison. It consists of a React and TypeScript frontend and a Python and FastAPI backend.

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

## Important implementation notes

- The catalog and account data use an in-process demonstration store.
- The cart and session state are kept in frontend memory and are reset when the page is reloaded.
- Checkout is simulated. No real payment is processed and no order is persisted.
- This root README was added after the frozen Stage 1 implementation baseline and is documentation only.
