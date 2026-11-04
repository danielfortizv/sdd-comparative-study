---
status: final
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-shift-bank-2026-10-20/prd.md
  - _bmad-output/planning-artifacts/prds/prd-shift-bank-2026-10-20/addendum.md
  - _bmad-output/planning-artifacts/ux-designs/ux-shift-bank-2026-10-20/DESIGN.md
  - _bmad-output/planning-artifacts/ux-designs/ux-shift-bank-2026-10-20/EXPERIENCE.md
  - _bmad-output/planning-artifacts/architecture/architecture-shift-bank-2026-10-20/ARCHITECTURE-SPINE.md
---

# Shift Bank (Stage 1) - Epic Breakdown

## Overview

This document provides the complete, authoritative epic and story breakdown for **Shift Bank (Stage 1)**. It translates the approved PRD requirements, UX visual and interaction design specifications (`DESIGN.md`, `EXPERIENCE.md`), and Architecture Decisions (`ARCHITECTURE-SPINE.md`) into implementable, vertically integrated stories organized by user value.

Every story is sized for single-agent completion, contains testable Gherkin-style Acceptance Criteria, strictly preserves BMAD's independent architectural decisions (USD currency, 3-account portfolio, integer cents precision, MFA lockout, dual-entry ledger), and enforces explicit dependency progression.

---

## Requirements Inventory

### Functional Requirements

- **FR-1**: Account Portfolio Listing — System retrieves and displays all 3 accounts (Primary Checking `CHK-1001`, High-Yield Savings `SAV-2001`, Emergency Reserve `RSV-3001`) owned by mock customer Alex Morgan (`cust_mock_001`).
- **FR-2**: Balance Currency Display — All balances are displayed strictly formatted in US Dollars ($ USD) with two decimal places using tabular numerals; backend values are stored as integer minor units (cents).
- **FR-3**: Transfer Formulation & Source/Destination Validation — Customer can formulate an internal transfer by selecting a Source Account, a distinct Destination Account, and an amount. Selecting identical accounts is prohibited in the UI and rejected by the API with HTTP 400 (`SAME_ACCOUNT_TRANSFER_NOT_ALLOWED`).
- **FR-4**: Transfer Amount Constraints — Transfer amount must be strictly greater than zero (`cents >= 1` / `$0.01`). Non-numeric, negative, or amounts with more than two decimal places are rejected with HTTP 422 (`INVALID_TRANSFER_AMOUNT`).
- **FR-5**: Fund Availability & Overdraft Prevention — The system verifies that the Source Account has sufficient available balance prior to execution or challenge issuance. Overdrafts are prohibited; insufficient funds return HTTP 422 (`INSUFFICIENT_FUNDS`).
- **FR-6**: Atomic Execution & Balance Conservation — Internal transfers execute within an isolated atomic transaction boundary (`BEGIN IMMEDIATE TRANSACTION`), ensuring $\sum B_{after} == \sum B_{before}$.
- **FR-7**: Duplicate Submission Protection — Frontend disables submit buttons and renders a loading spinner immediately upon click; backend validates and caches a 60-second client-generated `Idempotency-Key` (UUIDv4).
- **FR-8**: Sensitive Transfer Threshold Evaluation — Transfers with `amount <= $1,000.00` execute immediately (HTTP 200 `COMPLETED`); transfers with `amount > $1,000.00` persist in domain state `PENDING_MFA` and return HTTP 202 with API response status `MFA_REQUIRED`.
- **FR-9**: MFA Challenge Issuance & Verification Lifecycle — Generates an ephemeral challenge record with `challenge_id`, 300s TTL, and 3 attempts; user enters mock OTP `123456` in an accessible modal; successful verification executes the transfer atomically and updates domain state to `COMPLETED`.
- **FR-10**: MFA Challenge Expiration & Attempt Limits — Expiration after 300 seconds returns HTTP 410 (`MFA_CHALLENGE_EXPIRED`) and marks the transfer `FAILED`; incorrect code returns HTTP 400 with remaining attempts count; the 3rd failed attempt transitions to `EXHAUSTED` (HTTP 403) and marks the transfer `FAILED` with zero fund deductions.
- **FR-11**: MFA Challenge Abandonment & Cancellation — User can cancel or close the modal, triggering `POST /api/mfa/cancel`, which transitions the challenge and domain transfer to `CANCELLED` with zero fund deductions.
- **FR-12**: Chronological Movement Ledger Display — Movements for a selected account are displayed ordered chronologically descending (newest first, auto-increment ID tie-breaker), showing date, counterparty label, direction badge, signed amount, and post-transaction running balance.
- **FR-13**: Dual-Entry Movement Creation & Immutability — Every executed transfer generates exactly two linked immutable movement rows (`DEBIT` on source, `CREDIT` on destination) referencing the same `transfer_id`.
- **FR-14**: Zero-Movement State Presentation — Accounts with zero historical movements (specifically pre-seeded on Emergency Reserve `RSV-3001`) render an informative empty-state container with an embossed vault icon and explanatory copy rather than broken rows.

### Non-Functional Requirements

- **NFR-1**: Monetary Arithmetic Precision — Integer minor units (cents) enforced throughout backend models and calculations; binary floats are strictly banned; API serializes integer `cents` and exact 2-decimal strings.
- **NFR-2**: Transaction Atomicity & Concurrency — SQLite `BEGIN IMMEDIATE TRANSACTION` isolated ACID execution with row-level balance checks; 60-second server-side idempotency cache.
- **NFR-3**: Security & Session Isolation — Single mock customer boundary (Alex Morgan `cust_mock_001`) enforced via `X-Customer-Id` dependency; unauthorized account queries rejected with HTTP 403.
- **NFR-4**: UI Responsiveness & State Determinism — Optimistic balance rendering is prohibited; view state synchronizes only upon verified HTTP 200 responses; full WCAG 2.1 AA accessibility compliance.

### Additional Requirements from Architecture

- **AD-1**: Integer Minor Units for Monetary Precision (cents storage, string decimal serialization, `Intl.NumberFormat`).
- **AD-2**: ACID Transactional Atomicity & Balance Conservation Invariant ($\sum B_{after} == \sum B_{before}$).
- **AD-3**: Domain Transfer State Machine (`PENDING_MFA`, `COMPLETED`, `CANCELLED`, `FAILED`) decoupled from API response discriminator (`MFA_REQUIRED`, `COMPLETED`).
- **AD-4**: Mock Customer Context Boundary via `X-Customer-Id: cust_mock_001` HTTP header.
- **AD-5**: Idempotency Key (UUIDv4) caching with 60s TTL and client button loading lock.
- **AD-6**: Ephemeral MFA Challenge Lifecycle (300s TTL, 3 attempts, mock code `123456`, cancellation).
- **AD-7**: Immutable Dual-Entry Ledger with Auto-Increment Sequence ID Tie-Breaking.
- **AD-8**: Pre-Seeded Dataset Allocation for Immediate FR-14 Verification (Checking: 7 mvts, $2500; Savings: 3 mvts, $12450.75; Reserve: 0 mvts, $5000).
- **AD-9**: Prohibition of Optimistic Frontend State Updates.
- **AD-10**: Standardized JSON Error Envelope (`{ "error": { "code", "message", "details" } }`) mapped to semantic HTTP status codes (`400`, `403`, `410`, `422`).
- **Tech Stack Seed**: Python 3.11+, FastAPI 0.115.0, Pydantic 2.9.2, SQLite 3.45.0 (WAL mode), React 18.3.1, TypeScript 5.6.2, Vite 5.4.8, Pytest 8.3.3, Vitest 2.1.2.

### UX Design Requirements

- **UX-DR-1**: Design Token & Color Implementation — Implementation of `DESIGN.md` token system (Navy `#0A2540`, Cyan `#00D4B2`, Emerald `#059669`, Crimson `#DC2626`, spacing scale, radius scale, and tabular numeral typography `tabular-nums`).
- **UX-DR-2**: Executive 2-Column Dashboard Layout — Responsive top navigation bar (Alex Morgan identity badge), 3-card account grid, left transfer panel (40%), right movement ledger panel (60%).
- **UX-DR-3**: Reactive Account Card Selection — Clicking an account card sets active focus border (`{colors.border-active-card}`), updates the movement ledger, and pre-populates the transfer source.
- **UX-DR-4**: Transfer Form Interaction & Validation — Masked currency input, dynamic exclusion of selected source from destination selector, synchronous insufficient funds alert, instant button submit lock.
- **UX-DR-5**: Multi-State MFA Verification Modal — Focus-trapped accessible dialog, 300s countdown timer, 6 discrete OTP boxes with auto-advance, attempt badge, shake on error, and terminal lockout/timeout views.
- **UX-DR-6**: Empty-State Vault Component — Embossed vault illustration, headline, and explanatory text rendered for accounts with 0 movements.

---

## FR & Requirement Coverage Map

| Requirement / ID | Covered in Story | Primary Artifact / Rule |
|---|---|---|
| **FR-1** (Account Portfolio Listing) | Story 1.1, Story 1.2, Story 1.3 | PRD §4.1, AD-4, AD-8 |
| **FR-2** (Balance Currency Display) | Story 1.1, Story 1.2, Story 1.3 | PRD §4.1, AD-1, DESIGN.md (`mono-balance`) |
| **FR-3** (Transfer Formulation & Validation) | Story 2.1, Story 2.2 | PRD §4.2, AD-10, EXPERIENCE.md |
| **FR-4** (Transfer Amount Constraints) | Story 2.1, Story 2.2 | PRD §4.2, AD-1, AD-10 |
| **FR-5** (Fund Availability Check) | Story 2.1, Story 2.2 | PRD §4.2, AD-2, AD-10 |
| **FR-6** (Atomic Execution & Conservation) | Story 2.2, Story 2.3 | PRD §4.2, AD-2 |
| **FR-7** (Duplicate Submission Protection) | Story 2.2, Story 2.3 | PRD §4.2, AD-5 |
| **FR-8** (Sensitive Transfer Threshold) | Story 3.1 | PRD §4.3, AD-3, AD-6 |
| **FR-9** (MFA Verification Lifecycle) | Story 3.1, Story 3.2 | PRD §4.3, AD-3, AD-6 |
| **FR-10** (MFA Expiration & Limits) | Story 3.1, Story 3.3 | PRD §4.3, AD-6, AD-10 |
| **FR-11** (MFA Challenge Cancellation) | Story 3.2, Story 3.3 | PRD §4.3, AD-6 |
| **FR-12** (Chronological Movement Ledger) | Story 4.1, Story 4.2 | PRD §4.4, AD-7, AD-8 |
| **FR-13** (Dual-Entry Movement Creation) | Story 2.2, Story 4.1 | PRD §4.4, AD-2, AD-7 |
| **FR-14** (Zero-Movement State Presentation) | Story 4.1, Story 4.3 | PRD §4.4, AD-8, UX-DR-6 |
| **NFR-1** (Monetary Arithmetic Precision) | Story 1.1, Story 2.2, Story 4.1 | AD-1 |
| **NFR-2** (Transaction Atomicity & Concurrency) | Story 2.2 | AD-2, AD-5 |
| **NFR-3** (Security & Session Isolation) | Story 1.2 | AD-4 |
| **NFR-4** (UI Responsiveness & Sync) | Story 1.3, Story 2.3, Story 3.2 | AD-9, EXPERIENCE.md |
| **UX-DR-1** (Design Tokens & Typography) | Story 1.1, Story 1.3 | DESIGN.md |
| **UX-DR-2** (2-Column Dashboard Layout) | Story 1.3, Story 2.1, Story 4.2 | EXPERIENCE.md |
| **UX-DR-3** (Reactive Account Selection) | Story 1.3, Story 4.2 | EXPERIENCE.md |
| **UX-DR-4** (Transfer Form Interaction) | Story 2.1 | EXPERIENCE.md |
| **UX-DR-5** (MFA Modal Dialog) | Story 3.2, Story 3.3 | EXPERIENCE.md |
| **UX-DR-6** (Empty-State Component) | Story 4.3 | EXPERIENCE.md |

---

## Epic List

1. **Epic 1: Account Portfolio & Real-Time Balance Overview**  
   *User Outcome:* As Alex Morgan, I can view my banking accounts with verified, exact USD balances in a high-contrast executive dashboard, with my active account clearly selected.
2. **Epic 2: Intra-Customer Fund Transfers & Overdraft Prevention**  
   *User Outcome:* As Alex Morgan, I can reallocate money instantly between my own accounts (amounts $\le \$1,000.00$) with client-side balance validation, same-account protection, atomic backend execution, and instant feedback.
3. **Epic 3: Sensitive Transfer Step-Up Verification (Mock MFA)**  
   *User Outcome:* As Alex Morgan, when initiating a transfer exceeding $1,000.00, I am presented with an accessible step-up verification modal that accepts mock OTP `123456`, enforces a 300-second countdown, handles retries/lockout, and allows safe cancellation.
4. **Epic 4: Account Movement Ledger & Transaction History**  
   *User Outcome:* As Alex Morgan, I can review an immutable chronological ledger of all debits and credits for each account with running balances, and immediately observe a clean empty-state presentation for Emergency Reserve.

---

## Epic 1: Account Portfolio & Real-Time Balance Overview

**Goal:** Establish the foundational client-server architecture, seed the mock customer and account portfolio, expose the authenticated account portfolio API, and deliver the responsive dashboard UI displaying real-time balances with exact tabular typography.

### Story 1.1: Project Scaffolding, Design Tokens & Database Seeder

As a developer,  
I want to establish the Python FastAPI backend, SQLite persistence schema, React + TypeScript frontend with design tokens, and initialize the pre-seeded account portfolio,  
So that the application has a verified foundation and starts with accurate initial customer data.

**Acceptance Criteria:**

- **Given** a greenfield workspace,  
  **When** the backend initializes,  
  **Then** a FastAPI application is configured with SQLite running in WAL mode, foreign keys enabled, and integer cents column definitions (`AD-1`, `AD-2`).
- **And** the database seeder creates customer `cust_mock_001` ("Alex Morgan") and exactly 3 accounts:  
  1. `CHK-1001` (Primary Checking, balance: `250000` cents / $2,500.00)  
  2. `SAV-2001` (High-Yield Savings, balance: `1245075` cents / $12,450.75)  
  3. `RSV-3001` (Emergency Reserve, balance: `500000` cents / $5,000.00) (`AD-8`).
- **And** the frontend is initialized with Vite, React 18, and TypeScript, configured with the CSS custom property tokens defined in `DESIGN.md` (Navy `#0A2540`, Cyan `#00D4B2`, tabular numbers font scale) (`UX-DR-1`).
- **And** automated tests confirm that database initialization is idempotent and correctly asserts the three pre-seeded balances without float precision loss.

### Story 1.2: Account Portfolio API & Context Validation

As a retail customer (Alex Morgan),  
I want to query my bank accounts through a secure backend API,  
So that I retrieve the complete portfolio of my owned accounts with exact balances.

**Acceptance Criteria:**

- **Given** an authenticated API request with header `X-Customer-Id: cust_mock_001`,  
  **When** the client sends `GET /api/accounts`,  
  **Then** the backend responds with HTTP 200 and a JSON list of the 3 pre-seeded accounts:  
  `[{"id": "CHK-1001", "nickname": "Primary Checking", "type": "CHECKING", "balance_cents": 250000, "balance_formatted": "$2,500.00"}, ...]` (`FR-1`, `FR-2`, `AD-1`, `AD-4`).
- **And** all balance figures serialize as both integer `cents` and fixed two-decimal strings (`AD-1`).
- **And** if the request omits `X-Customer-Id` or provides an unknown ID, the endpoint responds with HTTP 403 Forbidden and the standardized error envelope (`AD-4`, `AD-10`).
- **And** automated unit and integration tests verify response payload schemas and customer boundary enforcement.

### Story 1.3: Responsive Account Portfolio Grid & Selection UI

As a retail customer (Alex Morgan),  
I want to view my accounts in a responsive card grid on the dashboard and select an active account,  
So that I can see my balances at a glance and focus the workspace on a specific account.

**Acceptance Criteria:**

- **Given** the frontend application loads in a browser,  
  **When** the dashboard initializes,  
  **Then** the top navigation bar displays the Shift Bank brand, the "Stage 1 Sandbox" tag, and customer badge "Alex Morgan (`cust_mock_001`)" (`UX-DR-2`).
- **And** the account portfolio grid displays 3 cards (`Primary Checking`, `High-Yield Savings`, `Emergency Reserve`) formatted with `{components.account-card}` styling and tabular numeral balances (`FR-1`, `FR-2`, `UX-DR-1`).
- **And** clicking an account card activates that card, applying `{colors.border-active-card}` (2px solid Navy ring) and updating the active account state in the application store (`UX-DR-3`).
- **And** keyboard navigation (`Tab`, `Enter`, `Space`) permits traversing and selecting account cards with visible focus rings complying with WCAG 2.1 AA (`NFR-4`).

---

## Epic 2: Intra-Customer Fund Transfers & Overdraft Prevention

**Goal:** Enable the customer to formulate and execute immediate own-account transfers ($\le \$1,000.00$) with client-side input validation, dynamic same-account restriction, atomic database transactions, duplicate submission locking, and real-time balance synchronization.

### Story 2.1: Transfer Form UI with Source/Destination Locks & Client Validation

As a retail customer (Alex Morgan),  
I want to formulate a transfer between my owned accounts with real-time field validation,  
So that I cannot accidentally select the same account or submit invalid/overdraft amounts.

**Acceptance Criteria:**

- **Given** the customer views the Transfer Action Panel,  
  **When** the customer selects a Source Account in the dropdown,  
  **Then** the Destination Account dropdown dynamically disables or excludes the chosen Source Account, making self-transfer impossible in the UI (`FR-3`, `UX-DR-4`).
- **And** the Amount field restricts input to positive numbers with at most 2 decimal places, rejecting negative numbers or non-numeric characters (`FR-4`).
- **And** if the customer inputs an amount exceeding the Source Account balance, an inline warning displays: *"Insufficient funds ($X,XXX.XX available)"*, and the submit button is disabled (`FR-5`, `UX-DR-4`).
- **And** if the customer inputs an amount $> \$1,000.00$, the submit button label dynamically updates to *"Verify & Transfer ($X,XXX.XX)"* with an amber sensitivity badge (`FR-8`, `UX-DR-4`).

### Story 2.2: Atomic Transfer Service & Balance Conservation Backend

As a system,  
I want to execute valid intra-customer transfers within an isolated ACID database transaction,  
So that source and destination balances update simultaneously without risk of partial execution, overdraft, or float drift.

**Acceptance Criteria:**

- **Given** a valid transfer request `POST /api/transfers` with `from_account_id`, `to_account_id`, `amount_cents` ($\le 100000$), and header `Idempotency-Key: UUIDv4`,  
  **When** the transfer is processed,  
  **Then** execution occurs within a single SQLite `BEGIN IMMEDIATE TRANSACTION` boundary (`AD-2`).
- **And** source account balance decrements by `amount_cents` and destination account balance increments by `amount_cents` (`FR-6`).
- **And** two linked movement records (`DEBIT` on source, `CREDIT` on destination) referencing `transfer_id` are created atomically (`FR-13`, `AD-7`).
- **And** the balance conservation invariant ($\sum B_{after} == \sum B_{before}$) is verified before commit (`AD-2`).
- **And** if `from_account_id == to_account_id`, the API returns HTTP 400 (`SAME_ACCOUNT_TRANSFER_NOT_ALLOWED`) (`FR-3`, `AD-10`).
- **And** if `amount_cents <= 0`, the API returns HTTP 422 (`INVALID_TRANSFER_AMOUNT`) (`FR-4`, `AD-10`).
- **And** if `amount_cents > source_account.balance_cents`, the API returns HTTP 422 (`INSUFFICIENT_FUNDS`) (`FR-5`, `AD-10`).
- **And** submitting a duplicate request with the identical `Idempotency-Key` within 60 seconds returns the cached response without re-executing balances (`FR-7`, `AD-5`).

### Story 2.3: End-to-End Transfer Execution & View Synchronization

As a retail customer (Alex Morgan),  
I want to execute a transfer and immediately see confirmed balances across my dashboard,  
So that I have verified confidence that my funds have been accurately moved.

**Acceptance Criteria:**

- **Given** the customer clicks "Transfer Funds" for a transfer $\le \$1,000.00$,  
  **When** the request is dispatched,  
  **Then** the submit button immediately enters a disabled state displaying an animated spinner and *"Processing Transfer..."* to prevent double-clicks (`FR-7`, `UX-DR-4`).
- **And** upon receiving HTTP 200 OK (`status: "COMPLETED"`), the form resets its amount field and an emerald confirmation toast appears: *"Transfer of $250.00 to Primary Checking completed. Reference: TRF-XXXX"* (`FR-6`, `EXPERIENCE.md`).
- **And** the account portfolio cards update their displayed balances synchronously without optimistic guessing (`AD-9`, `NFR-4`).
- **And** the updated balance cards display a subtle 400ms accent highlight flash (`{colors.accent}`) to confirm the update (`EXPERIENCE.md`).

---

## Epic 3: Sensitive Transfer Step-Up Verification (Mock MFA)

**Goal:** Implement step-up verification for high-value transfers ($> \$1,000.00$), issuing an ephemeral challenge, rendering an accessible modal dialog, validating mock OTP `123456`, enforcing expiration and attempt limits, and providing safe cancellation.

### Story 3.1: Sensitive Transfer Routing & Challenge Issuance Backend

As a system,  
I want to detect transfers exceeding $1,000.00 and issue a transient MFA challenge,  
So that high-value funds are not moved until verified by the step-up protocol.

**Acceptance Criteria:**

- **Given** a request to `POST /api/transfers` with `amount_cents > 100000` (e.g., $1,500.00),  
  **When** the source account has sufficient funds,  
  **Then** the backend persists the transfer in domain state `PENDING_MFA` without modifying account balances (`FR-8`, `AD-3`).
- **And** the backend generates an `MfaChallenge` record with `challenge_id`, `transfer_id`, `expires_at` (now + 300 seconds), `remaining_attempts: 3`, and `status: PENDING` (`FR-9`, `AD-6`).
- **And** the endpoint responds with HTTP 202 Accepted and JSON payload containing API initiation status `status: "MFA_REQUIRED"`, `challenge_id`, and transfer summary metadata (`AD-3`).
- **And** automated backend tests confirm that sensitive transfers never decrement account balances upon initial initiation.

### Story 3.2: MFA Modal Dialog & Verification Flow

As a retail customer (Alex Morgan),  
I want to review transfer details in an MFA modal and enter the 6-digit verification code,  
So that I can authorize my sensitive transfer safely.

**Acceptance Criteria:**

- **Given** the transfer API returns HTTP 202 `MFA_REQUIRED`,  
  **When** the client processes the response,  
  **Then** the MFA Verification Modal renders over a blurred backdrop, trapping keyboard focus within the dialog (`FR-9`, `UX-DR-5`).
- **And** the modal displays the transfer summary pill (e.g., "Checking → Emergency Reserve: $1,500.00"), a live countdown timer starting at 05:00 (300 seconds), an attempts badge ("3 attempts remaining"), and 6 discrete OTP input boxes (`UX-DR-5`).
- **And** focus auto-advances across the 6 OTP input boxes as digits are typed (`UX-DR-5`).
- **And** submitting the recognized mock OTP (`123456`) calls `POST /api/mfa/verify`, which transitions the challenge to `VERIFIED`, atomically executes the transfer, transitions the domain transfer state to `COMPLETED`, and returns HTTP 200 OK (`FR-9`, `AD-3`, `AD-6`).
- **And** the modal shows a success banner and closes, triggering balance updates across the account cards (`Primary Checking` becomes $1,000.00, `Emergency Reserve` becomes $6,500.00) (`UJ-3`).

### Story 3.3: MFA Retry, Expiration, Lockout & Cancellation Handling

As a retail customer (Alex Morgan),  
I want clear feedback if an MFA code is wrong, expired, or locked, and the ability to cancel safely,  
So that I understand my security status and my balances remain protected at all times.

**Acceptance Criteria:**

- **Given** the MFA modal is active,  
  **When** the customer submits an incorrect OTP (e.g., `999999`),  
  **Then** the backend decrements `remaining_attempts` and returns HTTP 400 with `{"error": {"code": "MFA_INVALID_CODE", "details": {"attempts_remaining": 2}}}` (`FR-10`, `AD-6`, `AD-10`).
- **And** the frontend OTP boxes shake horizontally for 300ms, highlight red (`{colors.destructive}`), display the remaining attempts warning, and reset focus to the first box (`UX-DR-5`).
- **And** on the 3rd failed attempt, the challenge transitions to `EXHAUSTED` (HTTP 403 `MFA_ATTEMPTS_EXHAUSTED`), the transfer transitions to `FAILED`, and the modal displays a terminal locked message with no funds debited (`FR-10`, `AD-6`).
- **And** if 300 seconds elapse before verification, submitting a code returns HTTP 410 (`MFA_CHALLENGE_EXPIRED`), marking the transfer `FAILED` with zero fund deductions (`FR-10`, `AD-6`).
- **And** if the customer clicks "Cancel Transfer" or presses `Escape`, the frontend calls `POST /api/mfa/cancel`, the backend marks the challenge and transfer `CANCELLED`, and the user returns to the form with original balances untouched (`FR-11`, `AD-6`).

---

## Epic 4: Account Movement Ledger & Transaction History

**Goal:** Implement the immutable dual-entry movement ledger, expose the per-account movement API with descending chronological sorting and sequence tie-breaking, deliver the ledger UI with running balances, and present the out-of-the-box empty state for Emergency Reserve.

### Story 4.1: Dual-Entry Movement Persistence & History API

As a system,  
I want to persist immutable debit/credit movement rows for each transfer and expose them per account,  
So that customers can audit their historical account activity with complete integrity.

**Acceptance Criteria:**

- **Given** the database seeder runs on initial startup,  
  **When** seed data is created,  
  **Then** the database inserts exactly 7 pre-seeded movements for Primary Checking (`CHK-1001`), exactly 3 pre-seeded movements for High-Yield Savings (`SAV-2001`), and exactly 0 movements for Emergency Reserve (`RSV-3001`) (`AD-8`).
- **And** when a client calls `GET /api/accounts/{account_id}/movements`, the backend returns HTTP 200 with the chronological movement list for that account, ordered strictly by `timestamp` descending, with auto-increment `id` descending as tie-breaker (`FR-12`, `AD-7`).
- **And** each movement item in the response contains: `id`, `transfer_id`, `direction` (`DEBIT` or `CREDIT`), `amount_cents`, `amount_formatted`, `running_balance_cents`, `running_balance_formatted`, `counterparty_label`, and `timestamp` (`FR-12`, `AD-1`, `AD-7`).
- **And** any attempt to update or delete movement rows via HTTP returns HTTP 405 Method Not Allowed (`FR-13`).

### Story 4.2: Chronological Movement Ledger UI

As a retail customer (Alex Morgan),  
I want to review the transaction history of my selected account in a clear tabular view,  
So that I can see the date, description, direction, amount, and running balance for every movement.

**Acceptance Criteria:**

- **Given** the customer selects an account card (e.g., Primary Checking or High-Yield Savings),  
  **When** the movement ledger loads,  
  **Then** transactions render in a table with columns: Date, Description/Counterparty, Direction, Amount, and Balance (`FR-12`, `UX-DR-2`).
- **And** credit movements render with emerald badges (`CREDIT`) and green signed amounts (`+$X.XX`), while debit movements render with neutral slate badges (`DEBIT`) and slate signed amounts (`-$X.XX`) (`DESIGN.md`, `EXPERIENCE.md`).
- **And** running balances display right-aligned using tabular monospace typography (`{typography.mono-amount}`) with zero column jitter (`UX-DR-1`).
- **And** switching between account cards immediately updates the ledger to reflect that specific account's movements (`UX-DR-3`).

### Story 4.3: Zero-Movement State Presentation (FR-14 Verification)

As a retail customer (Alex Morgan),  
I want to see an informative, reassuring empty state when viewing an account with no transactions,  
So that I know the account is active and simply has no transaction history yet.

**Acceptance Criteria:**

- **Given** the application initializes with the pre-seeded dataset,  
  **When** the customer clicks the `Emergency Reserve` account card (which has 0 seeded movements),  
  **Then** the movement table container is replaced by the Empty State Component (`FR-14`, `UX-DR-6`).
- **And** the empty state displays the embossed vault icon (`🏛️`), the heading *"No Transactions Yet"*, and the explanatory copy: *"This account does not have any recorded transaction activity. Completed transfers will appear here chronologically."* (`EXPERIENCE.md`, `mockups/dashboard.html`).
- **And** no broken tables, empty rows, or null values are displayed (`FR-14`).
- **And** when a transfer into Emergency Reserve is subsequently completed (e.g. following UJ-3), the empty state automatically transitions to the populated movement table showing the new credit movement (`FR-14`).
