# Stage 1 E-Commerce Demo

A local demonstration e-commerce application built with a React and TypeScript frontend and a Python/FastAPI backend.

The application includes:

- A public product catalog.
- A local shopping cart.
- Basic registration, sign-in, and sign-out.
- Cart preservation during authentication.
- A simulated checkout with no real payment or monetary charge.

## Requirements

Install the following software before running the project:

- Python 3.10 or newer.
- Node.js 18 or newer.
- npm.

## Project structure

```text
backend/    FastAPI application and SQLite user storage
frontend/   React, TypeScript, and Vite application
```

## Run the backend

Open a PowerShell terminal in the project root and run:

```powershell
Set-Location .\backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Keep this terminal open while using the application.

Backend URLs:

- API: <http://127.0.0.1:8000/api/products>
- Interactive API documentation: <http://127.0.0.1:8000/docs>

If the `py` launcher is unavailable, replace `py` with `python` when creating the virtual environment.

## Run the frontend

Open a second PowerShell terminal in the project root and run:

```powershell
Set-Location .\frontend
npm install
npm run dev
```

Open the URL displayed by Vite, normally:

<http://localhost:5173>

Both the backend and frontend terminals must remain running.

## Stop the application

Press `Ctrl+C` in each terminal.

## Local generated files

The following local files and directories should not be committed:

```text
backend/.venv/
backend/users.db
frontend/node_modules/
frontend/dist/
```

## Current baseline note

Development mode is available for reviewing the application. The frozen first-implementation baseline has a known TypeScript unused-import error in the production build command. That issue is intentionally pending correction through the approved BMAD workflow rather than through a manual source edit.

