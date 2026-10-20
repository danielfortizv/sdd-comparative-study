# PRD Addendum: Technical Depth & Decision Rationale

This document captures architectural handoffs, rejected alternatives, technical design considerations, and options-considered matrices that inform downstream workflows (`bmad-ux`, `bmad-architecture`, and `bmad-create-epics-and-stories`).

---

## 1. Options Considered & Rejected Alternatives

### 1.1 Monetary Precision & Datatypes
- **Option A (IEEE-754 standard floats / JS Numbers)**: Rejected. Floating-point arithmetic produces binary rounding anomalies (e.g., `0.1 + 0.2 = 0.30000000000000004`). In financial ledgers, this causes cumulative balance drift and reconciliation failures.
- **Option B (String-only arithmetic)**: Viable but computationally inefficient and requires custom comparison routines.
- **Chosen Alternative (Integer Cents internally + Decimal serialization)**: Balances and transaction amounts are represented internally as integer minor units (e.g., $100.50 = `10050` cents). Serialized via API as integer `cents` alongside an exact formatted decimal string (`"100.50"`). This guarantees zero rounding error across Python and TypeScript.

### 1.2 Sensitive Transfer & MFA Trigger Architecture
- **Option A (Cumulative Daily Limit Tracking)**: Tracking cumulative 24-hour transfer volume to trigger MFA requires persistent sliding-window state, time-zone alignment, and complex boundary testing.
- **Option B (Every Transfer Triggers MFA)**: High friction; diminishes UX for simple routine intra-account reallocations (e.g., moving $10 from checking to savings).
- **Chosen Alternative (Deterministic Per-Transaction Threshold of > $1,000.00)**: Clean, unambiguous, and directly testable. Routine small reallocations execute instantly; large transfers trigger step-up verification. Cumulative daily limits are explicitly logged as a Stage 2 consideration.

### 1.3 MFA Mechanism Implementation
- **Option A (External SMS/Email Gateway)**: Dependency on Twilio, AWS SNS, or SMTP servers introduces configuration overhead, costs, network latency, and non-deterministic failures in CI/CD test pipelines.
- **Option B (TOTP Authenticator App via QR Code)**: Requires authenticator app pairing and time-syncing, which adds unnecessary complexity for an already-authenticated mock user stage.
- **Chosen Alternative (Simulated Mock OTP with Deterministic Code)**: The server issues an MFA challenge with an ephemeral `challenge_id`. The client prompts for an OTP and accepts standard mock code `123456` (while optionally returning `mock_code_hint` in development mode for automated test harnesses).

### 1.4 API Protocol & Transfer Flow Pattern
- **Option A (Unified Single-Step POST with Optional OTP Header)**: Client submits transfer; if $> \$1,000$, server fails with 401/403 requiring client to re-post the entire payload with an MFA header. Causes repeated validation cycles.
- **Chosen Alternative (Two-Step State Machine: Initiate -> Verify)**:
  1. `POST /api/transfers`: Evaluates amount and funds. If $\le \$1,000$, executes immediately, sets domain transfer state to `COMPLETED`, and returns HTTP 200 with completed transfer (`status: "COMPLETED"`). If $> \$1,000$, persists the transfer entity in domain state `PENDING_MFA`, generates an MFA challenge, and returns HTTP 202 Accepted with API response status `status: "MFA_REQUIRED"`, `challenge_id`, and transfer preview.
     *(Architectural Clarification: `PENDING_MFA` is the persisted domain entity state; `MFA_REQUIRED` is the transient API initiation-response status instructing the client to prompt for MFA).*
  2. `POST /api/mfa/verify`: Accepts `challenge_id` and `code`. Upon verification, atomically finalizes transfer, transitions persisted transfer domain state from `PENDING_MFA` to `COMPLETED`, and returns HTTP 200 with completed transfer and updated balances.
  3. `POST /api/mfa/cancel`: Cancels pending challenge cleanly without deducting funds, transitioning persisted transfer domain state from `PENDING_MFA` to `CANCELLED`.

---

## 2. Technical Stack & Architectural Handoff Notes

### 2.1 Backend (Python / FastAPI)
- **Framework**: FastAPI (async support, native Pydantic schema validation, automatic OpenAPI documentation).
- **Domain Models**:
  - `Customer`: Fixed `cust_mock_001` ("Alex Morgan").
  - `Account`: `id`, `customer_id`, `account_number`, `nickname`, `type` (CHECKING, SAVINGS, RESERVE), `balance_cents` (Integer).
  - `Transfer`: `id`, `source_account_id`, `destination_account_id`, `amount_cents`, `status` (persisted domain states: `PENDING_MFA`, `COMPLETED`, `CANCELLED`, `FAILED`), `idempotency_key`, `created_at`.
  - `MfaChallenge`: `id`, `transfer_id`, `otp_code` (default `123456`), `expires_at`, `remaining_attempts` (default 3), `status` (PENDING, VERIFIED, EXPIRED, EXHAUSTED, CANCELLED).
  - `Movement`: `id`, `transfer_id`, `account_id`, `direction` (DEBIT, CREDIT), `amount_cents`, `running_balance_cents`, `counterparty_account_id`, `timestamp`.
- **Database / Persistence**: SQLite with WAL mode or in-memory repository with explicit transaction lock to simulate relational ACID constraints.

### 2.2 Frontend (React + TypeScript)
- **Framework & Build**: Vite + React + TypeScript.
- **State Management**:
  - Accounts & Balance store: Cached account list, refreshed automatically upon transfer completion.
  - Active Account selection: Drives Movement history pane.
  - Transfer State Machine:
    - `IDLE` -> `SUBMITTING` -> `SUCCESS` (if $\le \$1,000$, API returns `COMPLETED`)
    - `IDLE` -> `SUBMITTING` -> (API returns `MFA_REQUIRED`, persisted transfer in `PENDING_MFA`) -> `MFA_PROMPT` -> `VERIFYING` -> `SUCCESS` (if $> \$1,000$)
    - Error branches: `INSUFFICIENT_FUNDS`, `SAME_ACCOUNT`, `MFA_INVALID_CODE`, `MFA_EXHAUSTED`, `MFA_EXPIRED`.
- **UX & Accessibility**:
  - Form validation: Destination selector disables currently selected Source account.
  - Amount input: Masked currency input preventing negative values and non-digit characters.
  - Modals: Accessible dialog trapping focus during MFA verification with clean backdrop dismissal or Escape-key cancellation.

### 2.3 Pre-Seeded Dataset & Movement Allocation
- **Customer**: Alex Morgan (`cust_mock_001`)
- **Accounts & Initial Balances**:
  - `CHK-1001` (Primary Checking): $2,500.00 (`250000` cents), 7 pre-seeded movements (simulating payroll deposit, utility debit, grocery debit, previous small transfer, coffee, dining, subscription; net sum $2,500.00).
  - `SAV-2001` (High-Yield Savings): $12,450.75 (`1245075` cents), 3 pre-seeded movements (simulating opening principal deposit, monthly interest credit, intra-account transfer; net sum $12,450.75).
  - `RSV-3001` (Emergency Reserve): $5,000.00 (`500000` cents), 0 pre-seeded movements (established as untouched initial reserve capital).
- **Testability Alignment**: By assigning exactly 0 movements to Emergency Reserve, FR-14 (Zero-Movement State Presentation) is verifiable immediately out-of-the-box upon selecting Emergency Reserve in the UI.
