---
title: 'Story 1.1: Project Scaffolding, Design Tokens & Database Seeder'
type: 'feature'
created: '2026-10-20'
status: 'done'
route: 'dispatch'
review_loop_iteration: 1
context:
  - '_bmad-output/planning-artifacts/architecture/architecture-shift-bank-2026-10-20/ARCHITECTURE-SPINE.md'
  - '_bmad-output/planning-artifacts/ux-designs/ux-shift-bank-2026-10-20/DESIGN.md'
  - '_bmad-output/implementation-artifacts/epic-1-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Shift Bank Stage 1 lacks a foundational codebase, persistence layer, and frontend structure to host core banking functionality.

**Approach:** Scaffold the Python FastAPI backend with SQLite (WAL mode, integer cents schema), seed mock customer Alex Morgan (`cust_mock_001`) with the three approved accounts (Checking, Savings, Reserve), initialize the React + TypeScript frontend with Vite and `DESIGN.md` CSS custom properties, and verify seeder correctness via automated tests.

## Boundaries & Constraints

**Always:**
- Use integer minor units (cents) for all stored monetary values (`AD-1`).
- Enforce foreign keys and WAL mode in SQLite (`AD-2`).
- Seed customer `cust_mock_001` with exactly: Primary Checking ($2,500.00 / 250,000 cents), High-Yield Savings ($12,450.75 / 1,245,075 cents), and Emergency Reserve ($5,000.00 / 500,000 cents) (`AD-8`).
- Configure frontend tokens matching `DESIGN.md` exactly (`Navy #0A2540`, `Cyan #00D4B2`, tabular numerals) (`UX-DR-1`).
- Guarantee seeder idempotency.

**Never:**
- Never use floating-point types (`float`) for monetary amounts.
- Never modify or use any Kiro artifacts or source code.
- Never create unapproved accounts or change initial balances.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Fresh DB Init | Empty database | Creates tables `customer`, `account`, `transfer`, `mfa_challenge`, `movement` and seeds 1 customer + 3 accounts | Rolls back on error |
| Idempotent Re-seed | Existing populated DB | Re-running seeder detects existing customer/accounts and does not duplicate or overwrite rows | No-op / safe skip |
| Balance Precision | Database query | Checking: `250000`, Savings: `1245075`, Reserve: `500000` integer cents | Test assertion failure if drift |

</frozen-after-approval>

## Code Map

- `backend/app/main.py` -- FastAPI entry point and healthcheck route
- `backend/app/config.py` -- Database paths, mock customer ID, constants
- `backend/app/core/database.py` -- SQLite connection, PRAGMA wal, table DDL
- `backend/app/core/seed.py` -- Idempotent seeding logic for customer and accounts
- `backend/app/domain/models.py` -- Core domain dataclasses / schemas
- `backend/requirements.txt` -- FastAPI, Uvicorn, Pydantic, pytest
- `backend/tests/test_seed.py` -- Automated test verifying schema and seeder integrity
- `frontend/package.json` -- React, TypeScript, Vite configuration
- `frontend/vite.config.ts` -- Vite configuration with API proxy
- `frontend/src/styles/tokens.css` -- CSS custom properties mapped to `DESIGN.md` tokens
- `frontend/src/App.tsx` -- Root application shell

## Tasks & Acceptance

**Execution:**
- [x] `backend/requirements.txt` -- Define pinned dependencies (FastAPI 0.115.0, Uvicorn 0.31.0, Pydantic 2.9.2, pytest 8.3.3)
- [x] `backend/app/config.py` -- Define system settings and constants
- [x] `backend/app/core/database.py` -- Implement SQLite table creation and connection manager
- [x] `backend/app/core/seed.py` -- Implement idempotent seeder for Alex Morgan and 3 accounts
- [x] `backend/app/main.py` -- FastAPI app with startup lifecycle seeder execution
- [x] `backend/tests/test_seed.py` -- Automated test verifying seeder and integer balance precision
- [x] `frontend/package.json` -- Configure Vite + React 18 + TypeScript
- [x] `frontend/vite.config.ts` -- Setup dev server and `/api` reverse proxy to port 8000
- [x] `frontend/src/styles/tokens.css` -- Implement design tokens from `DESIGN.md`
- [x] `frontend/src/App.tsx` -- Shell layout with top bar brand and token integration

**Acceptance Criteria:**
- Given a clean environment, when backend tests run (`pytest`), then all seeder and schema assertions pass with 0 errors.
- Given the frontend runs, when inspecting styles, then the tokens for `--primary` (`#0A2540`), `--accent` (`#00D4B2`), and `tabular-nums` are active.

## Implementation Notes

- **Backend Scaffolding & Database Seeder**:
  - Implemented SQLite database layer with WAL mode and foreign key enforcement in `backend/app/core/database.py`.
  - Created tables: `customer`, `account`, `transfer`, `mfa_challenge`, `movement`, and `idempotency_cache`.
  - Created idempotent database seeder in `backend/app/core/seed.py`, establishing customer `cust_mock_001` ("Alex Morgan") and the three approved accounts: Primary Checking (`CHK-1001`, 250,000 cents), High-Yield Savings (`SAV-2001`, 1,245,075 cents), and Emergency Reserve (`RSV-3001`, 500,000 cents).
  - Configured FastAPI startup lifespan in `backend/app/main.py` and healthcheck endpoint `GET /api/health`.
  - Added automated test suite in `backend/tests/test_seed.py` verifying customer/account counts, balance precision, idempotency, non-negative balance constraints, and healthcheck. All 4 tests pass (`pytest`).
- **Frontend Scaffolding & Design Tokens**:
  - Initialized React 18.3.1 + TypeScript 5.5.3 + Vite 5.4.2 in `frontend/`.
  - Configured `/api` reverse proxy to `http://127.0.0.1:8000` in `frontend/vite.config.ts`.
  - Implemented `DESIGN.md` CSS custom properties and typography in `frontend/src/styles/tokens.css` (Navy `#0A2540`, Cyan `#00D4B2`, tabular numbers).
  - Built shell header and layout in `frontend/src/App.tsx` displaying brand and Alex Morgan customer badge.
  - Verified compilation and production build via `npm run build` (`tsc && vite build`) with 0 errors.
