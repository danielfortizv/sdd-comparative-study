# Epic 1 Context: Account Portfolio & Real-Time Balance Overview

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Establish the foundational client-server application architecture (FastAPI backend with SQLite WAL mode and React/TypeScript frontend), seed the mock retail customer profile and three initial accounts, expose the authenticated account portfolio API, and deliver the responsive dashboard UI displaying real-time balances with exact tabular typography.

## Stories

- Story 1.1: Project Scaffolding, Design Tokens & Database Seeder
- Story 1.2: Account Portfolio API & Context Validation
- Story 1.3: Responsive Account Portfolio Grid & Selection UI

## Requirements & Constraints

- **Account Holdings (FR-1, AD-8)**: System must represent mock customer Alex Morgan (`cust_mock_001`) with exactly three pre-seeded accounts:
  1. `CHK-1001` (Primary Checking): initial balance $2,500.00 (`250000` cents).
  2. `SAV-2001` (High-Yield Savings): initial balance $12,450.75 (`1245075` cents).
  3. `RSV-3001` (Emergency Reserve): initial balance $5,000.00 (`500000` cents).
- **Monetary Precision Policy (FR-2, NFR-1, AD-1)**: All balances and amounts must be stored, computed, and compared as integer minor units (cents). Floating-point arithmetic is strictly prohibited. API responses must serialize amounts as both integer `cents` and fixed two-decimal strings (e.g., `"2500.00"`).
- **Customer Context & Authorization (NFR-3, AD-4)**: Requests must supply `X-Customer-Id: cust_mock_001`. The backend extracts this header and rejects unauthorized or missing contexts with HTTP 403 Forbidden.
- **UI Performance & Accessibility (NFR-4)**: Visual components must meet WCAG 2.1 AA contrast requirements and support keyboard navigation. Optimistic balance guessing is banned.

## Technical Decisions

- **Backend Stack**: Python 3.11+, FastAPI 0.115.0, Uvicorn 0.31.0, Pydantic 2.9.2, SQLite 3.45.0 (WAL mode, foreign keys enabled).
- **Frontend Stack**: React 18.3.1, TypeScript 5.6.2, Vite 5.4.8, Axios / Native Fetch.
- **Error Formatting (AD-10)**: Standardized JSON envelope `{ "error": { "code": string, "message": string, "details": any } }`.
- **Database Schema**:
  - `customer`: `id` (PK, string), `full_name` (string), `email` (string).
  - `account`: `id` (PK, string), `customer_id` (FK, string), `nickname` (string), `account_type` (string), `balance_cents` (integer).

## UX & Interaction Patterns

- **Design System Tokens (`DESIGN.md`)**: Primary Navy (`#0A2540`), Action Cyan (`#00D4B2`), Background (`#F8FAFC`), Surface (`#FFFFFF`), Border (`#E2E8F0`), Active Card Border (`#0A2540`).
- **Typography**: Inter for interface elements; tabular numbers (`tabular-nums` / system monospace) for monetary figures to prevent layout jitter.
- **Card Selection**: Clicking an account card sets active focus border and persists selected account state in the frontend store.

## Cross-Story Dependencies

- Story 1.1 must establish the directory tree, database seeder, and design tokens before Story 1.2 can query the database.
- Story 1.2 must implement and verify `GET /api/accounts` before Story 1.3 wires the UI to live data.
