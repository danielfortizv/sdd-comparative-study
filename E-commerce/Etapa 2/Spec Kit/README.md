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

Stage 2 validation: 5 backend tests and 8 frontend tests passed. The production build passed with non-blocking ESLint warnings about two effect dependencies and an unused variable.
