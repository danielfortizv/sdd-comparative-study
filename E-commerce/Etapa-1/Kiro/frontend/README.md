# E-Commerce Stage 1 — Frontend (React + TypeScript)

Independently runnable and reviewable frontend application for the Stage 1
demonstration e-commerce journey. It owns all presentation and the locally
managed, in-memory cart and session state, and talks to the backend
exclusively over HTTP/JSON.

## Structure

```
src/
  views/              View layer — Catalog, Cart, Auth, Checkout components
  state/              In-memory journey state (cart + session, no persistence)
  api/                HTTP/JSON API client module (single backend boundary)
  types.ts            Shared domain types mirroring the backend models
  App.tsx             Application shell wiring views + journey state
  main.tsx            Entry point
```

The frontend never reaches the backend data store directly; it always goes
through the API client over HTTP/JSON (Requirements 14.3, 14.4).

## Prerequisites

- Node.js 18+ (developed against Node 22)

## Setup

```bash
npm install
```

## Run

```bash
npm run dev
```

The dev server runs at `http://localhost:5173` and expects the backend at
`http://localhost:8000` (see `src/api/client.ts`).

## Test

```bash
npm test
```

## Build

```bash
npm run build
```
