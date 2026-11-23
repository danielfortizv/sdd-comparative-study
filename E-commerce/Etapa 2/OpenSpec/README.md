# Stage 1 Academic Ecommerce

Academic e-commerce demonstration built with a React and TypeScript frontend and a FastAPI backend. It includes a product catalog, local shopping cart, basic authentication, and a simulated checkout.

> This project is for academic demonstration only. It does not process real payments and is not configured for production use.

## Requirements

- Node.js 22 or later
- npm
- Python 3.10 or later

## Project structure

```text
backend/    FastAPI API and SQLite database
frontend/   React, TypeScript, and Vite application
openspec/   OpenSpec planning artifacts
```

## Run the backend

Open a terminal in the project root and run:

### Windows PowerShell

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### macOS or Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend will be available at:

- API: `http://127.0.0.1:8000`
- Health check: `http://127.0.0.1:8000/health`
- Interactive API documentation: `http://127.0.0.1:8000/docs`

The SQLite database and demonstration product catalog are created automatically when the backend starts.

## Run the frontend

Keep the backend running. Open a second terminal in the project root and run:

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173` in a browser.

## Try the application

1. Browse the product catalog.
2. Add an available product to the cart.
3. Open the cart and proceed to checkout.
4. Register a new account or sign in with an account you created previously.
5. Complete the simulated checkout.

## Stage 2 Features: Reviews & Moderation

This application implements **Stage 2** with native OpenSpec changes.
- **Product Details & Star Ratings**: Click any product's title or image to view its expanded detail page, including average star rating and a list of approved reviews.
- **Write a Review**: Logged-in users can write a review on the product detail page, select a rating from 1 to 5 stars, type comments, and upload an optional image.
- **Local Base64 Uploads**: Images are processed locally and encoded to Base64 data URLs on submission to keep everything self-contained (no external service required).
- **Moderation Workflow**: Newly submitted reviews start in a `pending` state and are hidden from the product details page.
- **Moderator Dashboard**: First register an account with identifier **`moderator`** and a password of your choice, then sign in with that same password to access the dedicated Moderation Dashboard at `/moderation` or via the "Moderation" link in the header. The moderator can review, approve, or reject comments and images. Approved reviews immediately display on the product pages and update the product's average rating.

## Production build

To verify the frontend production build:

```bash
cd frontend
npm install
npm run build
```

The generated files will be placed in `frontend/dist/`.

## Stop the application

Press `Ctrl+C` in each terminal running the backend or frontend server.

