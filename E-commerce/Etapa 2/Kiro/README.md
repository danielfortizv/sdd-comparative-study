# E-Commerce Stage 1 + Stage 2

This repository contains a demonstration e-commerce application generated for the SDD tools comparison. It consists of a React and TypeScript frontend and a Python and FastAPI backend.

**Stage 1** delivers the core purchasing journey: browse the catalog, manage a local cart, register or sign in, and complete a simulated checkout.

**Stage 2** adds **product reviews with images and moderation** on top of Stage 1, without changing the Stage 1 journey. A signed-in customer can submit a review (star rating, text, optional title, and up to three images) for a product; every review enters a moderation queue; a moderator approves or rejects it; and only approved reviews are shown publicly on the product together with an aggregate rating summary. See the native specification in `.kiro/specs/ecommerce-stage2/` (requirements, design, tasks) and the inherited Stage 1 spec in `.kiro/specs/ecommerce-stage1/`.

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

## Stage 2: reviews, images, and moderation

### How to try it

1. Start the backend and frontend as described above (two terminals). The backend seeds a demonstration moderator account automatically at startup.
2. In the browser, open a product's **View details** panel in the Catalog. The expanded panel shows the product's approved reviews, a rating summary, and — when you are signed in as a customer — a review submission form.
3. **Submit a review** as a customer: register or sign in on the **Account** view, then expand a product, choose a rating, write the review text (optionally a title), optionally attach up to three images, and submit. The review is created as `pending` and is not yet publicly visible.
4. **Moderate** the review: sign out, then sign in with the moderator credentials below and open the **Moderation** destination in the top navigation. The pending review appears in the queue with its product, rating, text, images, and author. Approve it to make it publicly visible (and counted in the rating summary) or reject it to keep it hidden.
5. Re-open the product's details as any visitor: approved reviews and the rating summary are now shown.

### Moderator demonstration credentials

A single built-in moderator account is seeded at backend startup so the moderation workflow can be demonstrated immediately:

| Field | Value |
| --- | --- |
| Identifier | `moderator` |
| Password | `moderator123` |

These are a local-demo convenience defined in `backend/app/services/moderator_seed.py`. Sign in with them on the Account view; the **Moderation** view then becomes usable. A regular customer account cannot access moderation.

### Stage 2 endpoints (added additively over the Stage 1 six)

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/products/{id}/reviews` | Approved reviews + rating summary for a product |
| `POST` | `/products/{id}/reviews` | Submit a review (active customer session required) |
| `GET` | `/reviews/images/{imageId}` | Serve a stored review image |
| `GET` | `/moderation/reviews` | Pending moderation queue (moderator session required) |
| `POST` | `/moderation/reviews/{reviewId}/approve` | Approve a pending review (moderator) |
| `POST` | `/moderation/reviews/{reviewId}/reject` | Reject a pending review (moderator) |

## Important implementation notes

- The catalog, account, and review data use an in-process demonstration store; nothing is persisted durably across backend restarts.
- Review **image bytes** are the only on-disk artifact: they are written to the git-ignored folder `backend/app/data/review_images/` and served through the backend. No external object storage, CDN, or paid service is used.
- Review images are submitted as base64-encoded data in the JSON request, validated (type allow-list JPEG/PNG/GIF/WebP, max 2 MB, up to 3 per review), and only then stored.
- Moderation states are `pending`, `approved`, and `rejected`; a decision is terminal. A customer may submit at most one review per product, and submitted reviews cannot be edited or deleted. These and other delegated decisions are documented as assumptions A1–A8 in `.kiro/specs/ecommerce-stage2/requirements.md`.
- The cart and session state are kept in frontend memory and are reset when the page is reloaded.
- Checkout is simulated. No real payment is processed and no order is persisted.
- All interface text, code, comments, and specifications are in English.
