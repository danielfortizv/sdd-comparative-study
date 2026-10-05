# Neon Tetris Study (Stage 1, Option A)

An authoritative-backend browser-based Tetris study built with a Python FastAPI backend and a React with TypeScript frontend.

---

## System Requirements

- **Backend:** Python 3.12+
- **Frontend:** Node.js v18+ & npm

---

## 1. Quick Verification & Build

To run all backend tests and build the frontend production assets in a single step (on Windows), execute the automated batch script:

```powershell
.\run_tests_and_build.bat
```

This script automatically sets `PYTHONPATH`, runs all 13 backend unit/integration tests with `pytest`, and builds the React application with `npm run build`.

---

## 2. Backend Setup & Run

The backend is a state-authoritative FastAPI service that handles session mapping, collision detection, piece spawning, and row clearing.

### Install Dependencies
Activate the virtual environment and install the required dependencies (if not already done):
```powershell
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Run the FastAPI Server
Run the backend with Uvicorn:
```powershell
uvicorn main:app --reload --port 8000
```
The interactive API documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### Run Tests
To run the 13 backend tests manually:
```powershell
cd backend
$env:PYTHONPATH=".."
.\venv\Scripts\pytest . -v
```

---

## 3. Frontend Setup & Run

The frontend is a decoupled React, TypeScript, and Vite SPA that communicates with the FastAPI endpoints.

### Install Dependencies
```powershell
cd frontend
npm install
```

### Run in Development Mode
```powershell
npm run dev
```
The application will be accessible at [http://localhost:5173/](http://localhost:5173/).

### Run Linter
To verify zero warnings or lint errors:
```powershell
npm run lint
```

### Build for Production
To check for any TypeScript type errors and compile production assets:
```powershell
npm run build
```

---

## 4. Game Controls & Mechanics

- **ArrowLeft (`←`):** Moves the active piece 1 column left.
- **ArrowRight (`→`):** Moves the active piece 1 column right.
- **ArrowDown (`↓`):** Soft drops the active piece 1 row down.
- **Gravity Tick (500 ms):** Triggered automatically by the client, calling the backend `/tick` endpoint.
- **Lock-Down & Clear:** Blocked downward moves lock the active piece, trigger line-clears (up to 2 rows), and spawn the next random tetromino at `[0, 3]`.
- **Game Over:** Spawning a piece on top of settled cells transitions status to `game_over` and prompts a reset dialog.
