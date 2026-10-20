---
title: Shift Bank - Stage 1 Product Requirements Document
status: final
created: 2026-10-20
updated: 2026-10-20
---

# PRD: Shift Bank (Stage 1)

## 0. Document Purpose

This Product Requirements Document (PRD) defines the functional, behavioral, and domain requirements for **Stage 1** of **Shift Bank**, a greenfield retail banking web application. It serves as the single source of truth for product management, software engineering, architecture, and user experience design within the BMAD framework. 

The document employs strict domain vocabulary defined in the **Glossary (§3)**. Features are organized with globally numbered, stable IDs (**FR-1** through **FR-14**) to enable reliable downstream traceability in architectural design and user story authoring. Technical implementation choices, architecture mechanics, and rejected alternatives are preserved in the companion document `addendum.md`.

---

## 1. Vision

Modern banking interfaces often compromise financial integrity through ambiguous state transitions, imprecise rounding, or convoluted verification flows. **Shift Bank** is conceived as a reference-grade, high-integrity digital banking portal engineered with financial correctness as its core tenet.

For Stage 1, Shift Bank delivers an intuitive, highly responsive desktop/web portal for an already-authenticated retail customer. The product solves three primary daily banking needs:
1. **Immediate Financial Visibility**: Instantaneous overview of all owned accounts, available balances, and complete transactional movement histories.
2. **Frictionless Intra-Customer Liquidity**: Rapid, atomic movement of funds between the customer's own accounts (e.g., funding checking from savings, or sweeping surplus cash into reserve).
3. **Adaptive Transaction Security**: High-value and high-risk transfer operations are secured by an inline mock multi-factor authentication (MFA) step-up protocol, protecting capital without requiring cumbersome third-party authentication infrastructure during initial delivery.

By strictly scoping Stage 1 to a single authenticated customer and internal account transfers, the platform establishes rock-solid foundations for monetary arithmetic, double-entry ledger discipline, and transactional atomicity before multi-tenant and external payment features are introduced.

---

## 2. Target User

### 2.1 Jobs To Be Done (JTBD)
- **Functional (Financial Overview)**: *"When I access my banking dashboard, I want to clearly see all my accounts and their exact current balances in one view, so that I understand my immediate financial standing."*
- **Functional (Self-Fund Transfer)**: *"When I need to reallocate money between my accounts, I want to transfer an exact amount quickly and atomically, so that my funds are available immediately without risk of partial execution."*
- **Functional (Audit & History)**: *"When I review an account, I want to see an immutable, chronological record of every debit and credit, so that I can reconcile my balance and verify past transfers."*
- **Emotional & Contextual (Security & Trust)**: *"When I initiate a substantial transfer, I want clear verification through an MFA challenge, so that I feel confident sensitive operations are defended against accidental or unauthorized execution."*

### 2.2 Non-Users (Stage 1)
- **Unauthenticated / Anonymous Visitors**: Stage 1 does not offer public marketing pages, guest flows, or onboarding.
- **New Customer Registrants**: User registration and KYC (Know Your Customer) identity verification are out of scope.
- **External Counterparties**: Third-party payees, external bank account holders, billers, and merchants are strictly excluded.
- **Multi-Tenant Concurrent Users**: Stage 1 operates exclusively within the boundary of a single authenticated mock profile.

### 2.3 Key User Journeys

#### UJ-1. Morning Balance and Position Review
- **Persona + Context**: Alex Morgan, a retail banking customer, accesses Shift Bank on a desktop browser to review their liquid cash position across personal accounts.
- **Entry State**: Authenticated session pre-loaded for customer profile `cust_mock_001`.
- **Path**:
  1. Alex lands on the primary Dashboard.
  2. The system renders three pre-seeded accounts: Primary Checking, High-Yield Savings, and Emergency Reserve.
  3. Alex views each account's current balance formatted to two decimal places in USD.
  4. Alex clicks the High-Yield Savings card to view its recent activity.
- **Climax**: The system presents the complete chronological list of ledger movements for High-Yield Savings, with the running balance accurately reflecting past transactions.
- **Resolution**: Alex has immediate, verified confidence in their liquid net worth.
- **Edge Case**: If an account has no recorded movements, the ledger pane displays an informative empty state (*"No transactions found for this account"*) rather than a blank or broken container.

#### UJ-2. Routine Low-Value Transfer (Instant Execution)
- **Persona + Context**: Alex needs to move $250.00 from High-Yield Savings into Primary Checking to cover impending debit card expenses.
- **Entry State**: Authenticated on the Transfer screen or via an inline quick-transfer action.
- **Path**:
  1. Alex selects `High-Yield Savings` as the Source Account.
  2. Alex selects `Primary Checking` as the Destination Account (the system automatically prevents selecting Savings as the destination).
  3. Alex inputs `$250.00` into the transfer amount field.
  4. Alex submits the transfer.
  5. Because the transfer amount ($250.00) is below the sensitive transfer threshold ($\le \$1,000.00$), the system executes the transfer immediately within an atomic transaction.
- **Climax**: The transfer completes instantaneously; confirmation feedback displays the transfer reference ID and updated balances for both accounts.
- **Resolution**: Alex sees the Savings balance decreased by $250.00 and the Checking balance increased by $250.00. Both account movement lists display new corresponding debit and credit records.

#### UJ-3. Sensitive Transfer with Step-Up Mock MFA Verification
- **Persona + Context**: Alex decides to transfer $1,500.00 from Primary Checking into Emergency Reserve.
- **Entry State**: Authenticated on the Transfer screen.
- **Path**:
  1. Alex selects `Primary Checking` (balance: $2,500.00) and `Emergency Reserve`.
  2. Alex enters `$1,500.00` and clicks "Transfer Funds".
  3. The system checks available funds (sufficient: $1,500.00 <= $2,500.00), identifies that the amount exceeds the $1,000.00 sensitivity threshold, and triggers a step-up challenge.
  4. The UI displays the MFA Challenge Modal showing the transaction summary ($1,500.00 to Emergency Reserve) and prompts for a 6-digit one-time password (OTP).
  5. Alex enters the simulated 6-digit mock OTP (`123456`) and clicks "Confirm Transfer".
  6. The system verifies the code, completes the atomic transfer, debits Checking (new balance: $1,000.00), and credits Emergency Reserve (new balance: $6,500.00).
- **Climax**: The modal resolves with a prominent success banner, displaying Transfer Reference ID `TRF-XXXX` and updated account balances.
- **Resolution**: Funds are safely transferred; ledger movements reflect the verified operation.
- **Edge Case (Incorrect Code & Retry)**: If Alex enters `999999`, the system rejects the code, shows "Invalid verification code (2 attempts remaining)", and keeps the modal open. If Alex fails three consecutive times, the challenge is invalidated and the transfer is aborted without deducting funds.

#### UJ-4. Transfer Cancellation / Challenge Abandonment
- **Persona + Context**: Alex initiates a $1,500.00 transfer, encounters the MFA challenge modal, but realizes they selected the wrong destination account.
- **Entry State**: MFA Challenge modal active on screen.
- **Path**:
  1. Alex clicks "Cancel Transfer" or closes the modal.
  2. The frontend sends an explicit cancellation or discards the active challenge.
  3. The backend marks the challenge `CANCELLED`.
- **Climax**: No funds are debited from the source account; no ledger movements are created.
- **Resolution**: Alex is returned to the transfer form with their original account balances completely intact.

---

## 3. Glossary

Strict adherence to the following definitions is required across all specifications, architectural artifacts, and user stories. Synonyms are strictly prohibited.

- **Customer Profile**: The single authenticated mock user identity represented in Stage 1 (`cust_mock_001`, "Alex Morgan").
- **Account**: A discrete financial holding entity owned exclusively by the Customer Profile. Identified by an immutable Account Number (e.g., `CHK-1001`).
- **Account Type**: The domain category of an Account, restricted in Stage 1 to: `CHECKING`, `SAVINGS`, and `RESERVE`.
- **Balance**: The net settled monetary value of an Account, measured in USD. Stored and calculated as an exact integer of minor units (cents) to eliminate floating-point precision error.
- **Internal Transfer**: A monetary transaction moving funds exclusively from an owned Source Account to an owned Destination Account belonging to the same Customer Profile.
- **Transfer Domain State**: The persisted lifecycle status of an Internal Transfer entity stored in the database: `PENDING_MFA` (persisted sensitive transfer awaiting verification), `COMPLETED` (fully settled transfer), `CANCELLED` (abandoned or cancelled transfer), and `FAILED` (aborted transfer due to attempt exhaustion or system fault).
- **Transfer Initiation Status**: The API response status discriminator returned in the payload of `POST /transfers`. Returns `MFA_REQUIRED` when initiating a Sensitive Transfer that requires client step-up verification, or `COMPLETED` when a Standard Transfer has executed immediately.
- **Sensitive Transfer**: An Internal Transfer whose transfer amount is strictly greater than the predefined security threshold of **$1,000.00 USD** (100,000 cents).
- **Standard Transfer**: An Internal Transfer whose transfer amount is less than or equal to **$1,000.00 USD** ($\le 100,000$ cents).
- **MFA Challenge**: A transient security verification session generated by the backend when a Sensitive Transfer is initiated. Contains an identifier, expiry timestamp, attempt counter, and status.
- **Mock OTP**: A deterministic 6-digit verification code (`123456` or server-provided mock hint) accepted by the MFA verification endpoint to simulate SMS/authenticator verification without external dependencies.
- **Movement**: An immutable ledger entry recording a balance change on a single Account resulting from a completed Internal Transfer. Every transfer generates exactly two Movements: one `DEBIT` and one `CREDIT`.
- **Movement Direction**: The polarity of a Movement relative to the target Account: `DEBIT` (outflow/reduction) or `CREDIT` (inflow/addition).
- **Idempotency Key**: A unique client-generated UUID submitted with a transfer request to prevent accidental duplicate execution resulting from network retries or repeated user clicks.

---

## 4. Features & Functional Requirements

### 4.1 Feature 1: Account Portfolio & Balance Overview

**Description**: Provides the Customer Profile with a unified overview of all owned banking accounts. Displays real-time balances, account nicknames, account types, and masked identifiers. Realizes **UJ-1**.

#### FR-1: Account Portfolio Listing
The system must retrieve and display all Accounts owned by the Customer Profile upon dashboard load. Realizes UJ-1.
**Consequences (testable):**
- System returns exactly the three pre-seeded accounts for customer `cust_mock_001`: Primary Checking (`CHK-1001`), High-Yield Savings (`SAV-2001`), and Emergency Reserve (`RSV-3001`).
- System renders each account with: Account Nickname, Account Number (masked or formatted), Account Type, and Current Balance.
- System returns HTTP 200 with complete account structures within 300ms.

#### FR-2: Balance Currency & Precision Display
The system must present all Account balances formatted strictly in US Dollars ($ USD) with two fixed decimal places. Realizes UJ-1.
**Consequences (testable):**
- An internal balance of `250000` cents renders visually as `$2,500.00`.
- An internal balance of `1245075` cents renders visually as `$12,450.75`.
- Balances are never rounded or represented as floating-point scientific notation.

---

### 4.2 Feature 2: Own-Account Fund Transfers

**Description**: Enables the Customer Profile to transfer money between any two distinct owned accounts. Validates transfer amounts, verifies fund availability, prevents invalid account pairings, and ensures atomic transaction execution. Realizes **UJ-2**, **UJ-3**.

#### FR-3: Transfer Formulation & Source/Destination Validation
The Customer Profile can select a Source Account, a distinct Destination Account, and an amount in USD. Realizes UJ-2, UJ-3.
**Consequences (testable):**
- The system prohibits selecting the same account as both Source and Destination (`source_account_id == destination_account_id`).
- When a Source Account is chosen, the UI automatically filters out or disables that account in the Destination selector.
- If an API request is received with identical source and destination IDs, the backend rejects it with HTTP 400 Bad Request (`SAME_ACCOUNT_TRANSFER_NOT_ALLOWED`).

#### FR-4: Transfer Amount Constraints & Boundaries
The system must enforce strict positivity and precision on all transfer amount inputs. Realizes UJ-2.
**Consequences (testable):**
- The transfer amount must be strictly greater than zero (`amount >= 0.01` USD / `cents >= 1`).
- Submitting an amount of `$0.00` is rejected with HTTP 422 Unprocessable Entity (`INVALID_TRANSFER_AMOUNT`).
- Submitting a negative amount (e.g., `-$50.00`) is rejected with HTTP 422 Unprocessable Entity (`INVALID_TRANSFER_AMOUNT`).
- Amounts with more than two decimal places (e.g., `$10.555`) are rejected by client input masking and backend validation.

#### FR-5: Fund Availability & Overdraft Prevention
The system must verify that the Source Account has sufficient available balance to cover the transfer amount prior to initiating any execution or MFA challenge. Realizes UJ-2, UJ-3.
**Consequences (testable):**
- If `amount > source_account.balance`, the system rejects the operation immediately with HTTP 422 Unprocessable Entity (`INSUFFICIENT_FUNDS`).
- Overdraft balances are prohibited; an account balance must never fall below zero (`balance >= 0`).
- No MFA challenge is generated if the source account lacks sufficient funds.

#### FR-6: Atomic Execution & Balance Conservation
The system must execute valid Internal Transfers within an atomic transaction boundary, updating source and destination balances simultaneously. Realizes UJ-2, UJ-3.
**Consequences (testable):**
- Upon successful execution, `source_account.balance` decreases by `amount` and `destination_account.balance` increases by `amount`.
- Invariant: The sum of balances across all accounts owned by the Customer Profile before the transfer equals the sum after the transfer ($\sum B_{after} = \sum B_{before}$).
- If an error occurs during execution, all database changes roll back completely, leaving all balances unchanged.

#### FR-7: Duplicate Submission & Concurrency Protection
The system must prevent duplicate transfer execution from rapid successive user actions or network retries. Realizes UJ-2, UJ-3.
**Consequences (testable):**
- The frontend disables the transfer submit button and activates a pending state immediately upon click.
- Each transfer request includes an `Idempotency-Key` (UUIDv4). If a duplicate request with an identical idempotency key is received within a 60-second window, the backend returns the cached initial response without re-executing balances.

---

### 4.3 Feature 3: Sensitive Transfer Step-Up Verification (Mock MFA)

**Description**: Protects high-value internal transfers by requiring a mock multi-factor authentication step-up verification whenever a transfer exceeds the sensitive threshold. Realizes **UJ-3**, **UJ-4**.

#### FR-8: Sensitive Transfer Threshold Evaluation
The system must evaluate the transfer amount against the sensitivity threshold to determine execution path. Realizes UJ-2, UJ-3.
**Consequences (testable):**
- A transfer with `amount <= $1,000.00` (100,000 cents) is classified as a Standard Transfer, executes immediately without an MFA challenge, sets persisted transfer domain state to `COMPLETED`, and returns HTTP 200 OK with response status `status: "COMPLETED"`.
- A transfer with `amount > $1,000.00` (100,001 cents or more) is classified as a Sensitive Transfer; the transfer record is persisted in the domain store with state `PENDING_MFA`, and the transfer initiation endpoint returns HTTP 202 Accepted with API response status `status: "MFA_REQUIRED"` alongside the MFA challenge payload (`challenge_id`, expiration, and attempt metadata) to prompt client step-up verification.

#### FR-9: MFA Challenge Issuance & Verification Lifecycle
The system must issue a transient MFA challenge for Sensitive Transfers and verify the submitted Mock OTP. Realizes UJ-3.
**Consequences (testable):**
- The backend generates an MFA challenge record containing: `challenge_id`, `transfer_id`, `expires_at`, `remaining_attempts: 3`, and `status: PENDING`.
- The client displays an MFA verification modal showing transfer details (Amount, Source, Destination) and a 6-digit OTP input.
- Submitting the recognized Mock OTP (`123456`) transitions the challenge to `VERIFIED`, triggers atomic transfer execution, transitions the persisted transfer domain state from `PENDING_MFA` to `COMPLETED`, and returns HTTP 200 OK with transfer confirmation.

#### FR-10: MFA Challenge Expiration & Attempt Limits
The system must enforce strict time limits and rate-limiting on MFA challenge verification attempts. Realizes UJ-3.
**Consequences (testable):**
- The MFA challenge expires exactly 300 seconds (5 minutes) after creation. Submitting a code after 300 seconds returns HTTP 410 Gone (`MFA_CHALLENGE_EXPIRED`); transfer is aborted and funds remain untouched.
- Entering an incorrect OTP decrements `remaining_attempts` and returns HTTP 400 Bad Request with the remaining count (e.g., `attempts_remaining: 2`).
- Upon reaching 3 consecutive failed attempts, the challenge transitions to `EXHAUSTED` (HTTP 403 Forbidden); the persisted transfer domain state transitions from `PENDING_MFA` to `FAILED`, and the pending transfer is permanently voided without deducting funds.

#### FR-11: MFA Challenge Abandonment & Cancellation
The Customer Profile can explicitly cancel or abandon an active MFA challenge at any time without side effects. Realizes UJ-4.
**Consequences (testable):**
- Clicking "Cancel" or closing the MFA modal triggers a cancellation request or client-side abandonment.
- The challenge is marked `CANCELLED`, and the persisted transfer domain state transitions from `PENDING_MFA` to `CANCELLED`.
- No funds are debited from the Source Account; no Movements are recorded.
- The user is returned to the transfer form with inputs preserved or cleanly reset.

---

### 4.4 Feature 4: Account Movement & Transaction History

**Description**: Provides an immutable, chronological ledger of all debits and credits associated with each account. Realizes **UJ-1**, **UJ-2**, **UJ-3**.

#### FR-12: Chronological Movement Ledger Display
The system must retrieve and display the list of Movements associated with a selected Account, ordered chronologically descending. Realizes UJ-1.
**Consequences (testable):**
- Movements are sorted strictly by `timestamp` descending (newest first).
- If two movements have identical timestamps, tie-breaking sorts by auto-incrementing `movement_id` descending.
- Each movement item displays: Date/Time (ISO 8601 UTC formatted to local user time), Counterparty Account Nickname/Number, Direction (`DEBIT` or `CREDIT`), Amount (with appropriate polarity: `-$250.00` or `+$250.00`), and Post-Transaction Running Balance.
- Initial seed state distribution provides 7 movements for Primary Checking (`CHK-1001`) with a net running balance of $2,500.00, and 3 movements for High-Yield Savings (`SAV-2001`) with a net running balance of $12,450.75.

#### FR-13: Dual-Entry Movement Creation & Immutability
Every executed Internal Transfer must generate exactly two immutable Movements tied to the same Transfer Reference ID. Realizes UJ-2, UJ-3.
**Consequences (testable):**
- An internal transfer of $500.00 creates:
  1. A `DEBIT` movement on Source Account with `amount: 50000`, recording new balance after debit.
  2. A `CREDIT` movement on Destination Account with `amount: 50000`, recording new balance after credit.
- Both movements reference the identical `transfer_id`.
- Movements cannot be modified, edited, or deleted via any API endpoint (HTTP 405 Method Not Allowed on PUT/PATCH/DELETE).

#### FR-14: Zero-Movement State Presentation
The system must render a clear, user-friendly empty state when an Account has no historical Movements. Realizes UJ-1.
**Consequences (testable):**
- Emergency Reserve (`RSV-3001`) initializes with exactly 0 pre-seeded movements (with an initial opening balance of $5,000.00 established as baseline principal).
- When Emergency Reserve is selected in the UI upon first application load, the movement container displays an explanatory visual state ("No transaction history yet for this account").
- No broken tables, empty rows, or cryptic null values are displayed.
- FR-14 is immediately demonstrable and verifiable out-of-the-box upon initial application launch without manual database clearing.

---

## 5. Non-Goals (Explicit Out-of-Scope for Stage 1)

The following capabilities are explicitly excluded from Stage 1 to maintain architectural purity and strict comparative boundary conditions:

- **User Authentication Infrastructure**: No login page, signup flow, session token refresh, JWT signing/verification, password hashing, or forgotten password reset. The user is assumed already authenticated.
- **External Transfers**: No ACH, wire transfers, RTP, FedNow, or transfers to third-party accounts or external routing numbers.
- **Third-Party Bill Payments & Invoicing**: No merchant payments, utility bill pay, or recurring scheduled payments.
- **Additional Banking Products**: No credit cards, debit card issuance, physical card controls, loans, mortgages, certificates of deposit (CDs), or investment portfolios.
- **Multi-Currency & FX Exchange**: All operations are strictly USD denominated. No currency conversion, foreign exchange rates, or multi-currency wallets.
- **Real SMS / Hardware Authenticator Integration**: No live Twilio/SNS SMS gateways, TOTP authenticator apps (Google Authenticator), or WebAuthn/FIDO2 hardware keys. Mock MFA handles all step-up logic.
- **Account Creation / Deletion**: Pre-seeded accounts are fixed; users cannot open new checking/savings accounts or close existing accounts in Stage 1.

---

## 6. MVP Scope (Stage 1)

### 6.1 In Scope
- Single authenticated mock customer context (`cust_mock_001`, Alex Morgan).
- 3 pre-seeded accounts: Primary Checking, High-Yield Savings, Emergency Reserve.
- Real-time balance inquiry with exact 2-decimal USD formatting.
- Internal transfer between own accounts (prohibiting self-to-self, $\le 0$ amounts, and overdrafts).
- Deterministic sensitive transfer detection ($> \$1,000.00$).
- Inline Mock MFA challenge (modal dialog, 6-digit OTP `123456`, 5-minute expiry, 3-attempt limit, clean cancellation).
- Atomic transaction execution with balance conservation invariant.
- Account-specific movement history, chronologically sorted, dual-entry debit/credit ledger, with running balance and empty state handling.
- Python backend (FastAPI/Pydantic) and React + TypeScript frontend.

### 6.2 Out of Scope for MVP
- Everything listed under §5 Non-Goals.
- Push notifications, email receipts, and PDF statement generation.
- Search, filter by date range, or CSV export on transaction history (deferred to Stage 2).
- Dark mode toggle or theme customization.

---

## 7. Success Metrics & Validation

### Primary Metrics
- **SM-1 (Transfer Correctness & Balance Invariance)**: 100% of executed internal transfers maintain exact balance conservation ($\sum B_{after} == \sum B_{before}$), verified by automated end-to-end and unit ledger audits. Validates FR-5, FR-6, FR-13.
- **SM-2 (Zero Float Errors)**: 0.00% precision drift or floating-point rounding discrepancies across all balance and movement calculations. Validates FR-2, FR-4, FR-6.
- **SM-3 (MFA Step-Up Enforcement)**: 100% of transfers exceeding $1,000.00 trigger the MFA challenge; 0% of transfers exceeding $1,000.00 execute without successful MFA verification. Validates FR-8, FR-9, FR-10.

### Secondary Metrics
- **SM-4 (Transfer Completion Time)**: Standard transfers complete in $< 500\text{ ms}$; sensitive transfers complete in $< 1000\text{ ms}$ upon OTP submission. Validates FR-6, FR-9.

### Counter-Metrics (Do Not Optimize)
- **SM-C1 (MFA Bypassing for Speed)**: Do **not** optimize transfer speed or click count by auto-filling or skipping the MFA prompt on sensitive transfers. Friction is an intentional security control. Counterbalances SM-4.
- **SM-C2 (Permissive Overdraft Approvals)**: Do **not** increase transfer completion rates by allowing negative balances or soft overdrafts. Rejections due to insufficient funds are correct behavior. Counterbalances SM-1.

---

## 8. Cross-Cutting Non-Functional Requirements & Domain Constraints

### 8.1 Monetary Precision Policy (NFR-1)
- All monetary amounts stored, calculated, and manipulated in the backend domain model must use integer minor units (cents) or arbitrary-precision decimals (`Decimal`).
- Binary floating-point types (`float` in Python, standard `number` without cents conversion in JS) are strictly prohibited for monetary calculations.
- API payloads serialize monetary values as both integer cents and ISO formatted strings (`"1000.00"`) to prevent IEEE-754 precision degradation in JSON parsers.

### 8.2 Transaction Atomicity & Concurrency (NFR-2)
- All transfer operations must execute within an isolated ACID transaction boundary.
- Pessimistic row locking or atomic balance updates (`UPDATE account SET balance = balance - :amt WHERE id = :src AND balance >= :amt`) ensure concurrent requests cannot overdraft an account.
- Server-side idempotency cache rejects identical in-flight submissions within 60 seconds.

### 8.3 Security & Mock Session Boundaries (NFR-3)
- The backend validates that all queried accounts belong to the current authenticated customer profile (`cust_mock_001`). Cross-customer account access is architecturally prevented.
- MFA challenges are bound to a specific `transfer_id` and cannot be reused or applied to any other transfer.

### 8.4 UI Feedback & Accessibility (NFR-4)
- Form inputs validate synchronously (preventing negative values, excessive decimals, self-account selection).
- Destructive or sensitive actions provide clear loading states and disabled button locks during async requests.
- All monetary figures and status messages comply with WCAG 2.1 AA contrast standards.

---

## 9. Open Questions & Deferred Items

1. **[DEFERRED to Stage 2] Daily Cumulative Sensitivity Threshold**:
   - *Current Decision*: Only individual transactions $> \$1,000.00$ trigger MFA.
   - *Future Revisit*: Should cumulative daily transfers exceeding $2,500.00 also trigger MFA even if individual transfers are $\le \$1,000.00$? (Deferred to Stage 2 to keep Stage 1 deterministic).
2. **[DEFERRED to Stage 2] Transaction Filtering & Pagination**:
   - *Current Decision*: Stage 1 returns the full chronological movement list based on a fixed pre-seeded distribution across accounts: Primary Checking has 7 movements, High-Yield Savings has 3 movements, and Emergency Reserve has 0 movements (ensuring immediate verification of the FR-14 zero-movement empty state).
   - *Future Revisit*: Introduce date pickers, category filters, and pagination when movement volume grows.

---

## 10. Assumptions Index

- **[ASSUMPTION: Pre-Seeded Data]** (§4.1, §4.4, §9): The application initializes with 3 pre-configured accounts: Primary Checking ($2,500.00, 7 movements), High-Yield Savings ($12,450.75, 3 movements), and Emergency Reserve ($5,000.00, 0 movements), owned by Alex Morgan (`cust_mock_001`). This distribution ensures both populated ledger review (FR-12) and zero-movement empty states (FR-14) are directly testable out of the box.
- **[ASSUMPTION: Universal Mock OTP]** (§4.3): For Stage 1 testing and demonstration, the code `123456` serves as the universal valid mock OTP. In addition, the initiation response may provide a `mock_code_hint` for developer inspection.
- **[ASSUMPTION: Single Currency]** (§1, §3): All accounts and transactions operate exclusively in USD; no currency conversion or exchange rate calculations are required.
- **[ASSUMPTION: Ephemeral Mock MFA Store]** (§4.3): MFA challenges may be persisted in memory or in the local database with an automatic TTL expiration check.
- **[ASSUMPTION: Desktop-First Web Interface]** (§1): The frontend UI is optimized primarily for desktop and tablet browser viewports typical of online banking portals.
