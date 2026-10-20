---
name: Shift Bank
status: final
sources:
  - _bmad-output/planning-artifacts/prds/prd-shift-bank-2026-10-20/prd.md
  - _bmad-output/planning-artifacts/prds/prd-shift-bank-2026-10-20/addendum.md
updated: 2026-10-20
---

# Shift Bank — Experience Spine

## Foundation

Single-page responsive web application built with React and TypeScript. Shift Bank Stage 1 provides a consolidated, high-integrity retail banking portal for a single pre-authenticated customer, **Alex Morgan** (`cust_mock_001`). 

The application architecture prioritizes visual determinism and financial accuracy: no background session refresh, no third-party identity redirection, and no speculative balance optimistic updates. Every state change is verified by an atomic backend response before UI confirmation. `DESIGN.md` serves as the authoritative visual identity reference and token dictionary; this document specifies the complete information architecture, interaction mechanics, and behavioral state machines.

---

## Information Architecture

The application layout is structured as a unified executive dashboard view:

| Surface / Panel | Reached From | Purpose |
|---|---|---|
| **Top Navigation Bar** | Global persistent header | Displays Shift Bank brand, Stage 1 Sandbox environment tag, and customer profile identifier (`Alex Morgan / cust_mock_001`). |
| **Account Portfolio Grid** | Top section of main canvas | Displays 3 pre-seeded account cards (`Primary Checking`, `High-Yield Savings`, `Emergency Reserve`) with real-time balances. Clicking an account card sets it as the active focus for the Movement Ledger and defaults the transfer source account. |
| **Transfer Action Panel** | Left column of core workspace | Form to initiate intra-customer money transfers between owned accounts. Validates inputs, handles source/destination constraints, and triggers execution or MFA. |
| **Account Movement Ledger** | Right column of core workspace | Shows the chronological debit/credit transaction history for the currently selected account, including post-transaction running balances. |
| **MFA Verification Modal** | Triggered by Sensitive Transfer (> $1,000.00) | Modal overlay presenting transfer preview, countdown expiration timer, 6-digit OTP input, and retry counter. |
| **Feedback Toast Banner** | Top right floating | Transient non-blocking notifications for routine transfer completions and non-fatal operational alerts. |

Composition reference: `mockups/dashboard.html`. The spine wins on conflict.

---

## Voice and Tone

Microcopy is calm, direct, and authoritative. Banking requires clarity over personality:

| Context | Do | Don't |
|---|---|---|
| **Transfer Confirmation** | "Transfer of $250.00 to Primary Checking completed. Reference: TRF-1082." | "Money moved! You're all set! 🎉" |
| **MFA Prompt** | "High-value verification required. Enter the 6-digit code sent to your registered device." | "Security check! Whoops, hold on a second!" |
| **MFA Invalid Code** | "Invalid verification code. 2 attempts remaining." | "Wrong code! Try again." |
| **MFA Lockout / Exhaustion** | "Verification attempts exceeded. This transfer has been cancelled to protect your account." | "You are locked out!" |
| **MFA Expiration** | "Verification session expired. No funds were debited. Please initiate a new transfer." | "Time ran out! ⏰" |
| **Insufficient Funds** | "Insufficient funds in Primary Checking ($2,500.00 available)." | "You don't have enough money for this!" |
| **Self-Transfer** | "Destination account must be different from source account." | "Can't transfer money to itself." |
| **Empty Ledger State** | "No transaction history yet for this account." | "Nothing here yet! Start spending!" |

---

## Component Patterns

Behavioral rules. Visual styling inherits from `DESIGN.md.Components`.

| Component | Surface | Behavioral Rules |
|---|---|---|
| **Account Card** | Account Portfolio Grid | - Displays Account Nickname, masked account number (`•••• 1001`), account type badge (`CHECKING`, `SAVINGS`, `RESERVE`), and currency balance.<br>- Click selects this account as active: updates the Movement Ledger immediately and sets this account as default Source in the transfer form.<br>- Keyboard `Enter` or `Space` activates the card. Active card receives `{components.account-card.border-selected}`. |
| **Transfer Form** | Transfer Action Panel | - **Source Selector**: Dropdown listing all 3 owned accounts with available balance subtitles.<br>- **Destination Selector**: Dropdown listing owned accounts. **Dynamically excludes or disables the selected Source Account** so self-transfer is physically unselectable in UI.<br>- **Amount Input**: Number field formatted with dollar sign prefix. Restricts input to maximum 2 decimal places. Rejects negative numbers and non-numeric characters.<br>- **Submit Button**: Displays "Transfer Funds" for amounts $\le \$1,000.00$; dynamically updates to "Verify & Transfer" for amounts $> \$1,000.00$.<br>- **Submit Lock**: Immediately enters pending/loading state (`Submitting...`) with spinner upon click to prevent double submission. |
| **MFA Verification Modal** | Global Overlay (Modal) | - Traps keyboard focus within the dialog container.<br>- Background click or `Escape` key acts as explicit cancellation (aborts transfer, closes modal, returns to form with original balances intact).<br>- Displays transaction summary pill: Amount, Source Account, Destination Account.<br>- 6-digit OTP input auto-focuses first input cell and advances focus automatically on keystroke.<br>- Live countdown timer decrements from 300 seconds (5:00).<br>- Displays attempt pill ("3 attempts remaining"). |
| **Movement Table** | Movement Ledger Panel | - Renders movements in strictly chronological descending order (newest at top).<br>- Each row displays: formatted date/time, counterparty label (`From High-Yield Savings` or `To Emergency Reserve`), direction badge (`CREDIT` in `{colors.credit}` or `DEBIT` in `{colors.debit}`), signed amount (`+$250.00` in green / `-$250.00` in slate), and right-aligned running balance formatted with `{typography.mono-amount}`.<br>- Responsive: On narrow viewports, the running balance moves beneath the amount. |
| **Empty State Container** | Movement Ledger Panel | - Renders when selected account has 0 historical movements (specifically pre-seeded on `Emergency Reserve`).<br>- Centered layout featuring an embossed vault icon, bold heading ("No Transactions Yet"), and explanatory text ("This account does not have any recorded transaction activity."). |

---

## State Patterns

### 1. Account Portfolio States
- **Cold App Load**: Displays 3 skeleton shimmer cards matching account card geometry while data loads.
- **Active Focus**: Exactly one account card possesses the active focus indicator (`{colors.border-active-card}`). Defaults to Primary Checking on first load.
- **Balance Update**: When a transfer completes, affected account balances update smoothly in place, with a subtle 400ms highlight flash (`{colors.accent}`) to signal change.

### 2. Transfer Form States
- **Idle / Ready**: Source and Destination valid, amount blank or valid, submit button enabled.
- **Same Account Attempt**: Destination dropdown automatically disables the selected Source account. If manipulated via keyboard navigation, displays inline error: *"Destination account must be different from source account"*; submit disabled.
- **Insufficient Funds**: When entered amount exceeds `source_account.balance`, displays inline destructive message below amount input: *"Insufficient funds ($X,XXX.XX available)"*; submit button disabled.
- **Zero / Negative Amount**: Entering `0.00` or negative values shows inline validation error: *"Transfer amount must be at least $0.01"*; submit disabled.
- **Submitting Lock**: Submit button disabled, text replaced with animated spinner + *"Processing Transfer..."*. All form fields temporarily disabled until API response arrives.

### 3. MFA Modal Lifecycle States
- **MFA Challenge Active (Prompt)**: Modal rendered on top of blurred canvas. Displays transfer summary, countdown timer active (`04:59`), 6 empty input boxes, and *"3 attempts remaining"*.
- **MFA Submitting**: Upon entering 6th digit, the verification request dispatches automatically (or via Confirm button). Input cells lock with a spinner.
- **MFA Invalid Code (Retry)**:
  - Input cells shake horizontally for 300ms.
  - Border turns red (`{colors.destructive}`).
  - Warning banner displays: *"Invalid verification code. 2 attempts remaining."*
  - Cells clear and focus returns to the first digit.
- **MFA Exhausted (Lockout)**:
  - Triggered after 3 consecutive invalid attempts.
  - Modal switches to terminal error state: Red lock icon, headline *"Verification Locked"*, and body *"Maximum verification attempts exceeded. This transfer has been voided. No funds have been debited."*
  - Only action available is *"Close"*.
  - Closing dismisses the modal and returns the user to the transfer form with balances untouched.
- **MFA Expired**:
  - Countdown timer reaches `00:00` (after 300 seconds).
  - Modal updates to expired state: Yellow warning icon, headline *"Verification Expired"*, body *"This verification session has timed out. The transfer was cancelled. No funds were debited."*
  - Primary button: *"Return to Dashboard"*.
- **MFA Cancelled / Dismissed**:
  - User clicks *"Cancel Transfer"*, presses `Escape`, or clicks the backdrop.
  - A modal dismiss animation executes; backend receives challenge cancellation or abandons challenge.
  - Zero balance changes. User returns to transfer form with original fields retained.

### 4. Movement History States
- **Populated Ledger**: Renders chronological table with pagination/scroll (Checking: 7 seed movements; Savings: 3 seed movements).
- **Zero-Movement Empty State**: When Emergency Reserve is clicked, table is replaced by the Empty State container demonstrating **FR-14** immediately out of the box.

---

## Interaction Primitives

### Keyboard Navigation
- `Tab` / `Shift+Tab`: Strictly cycles through interactive elements in visual order.
- `Escape`: Universally closes the active MFA modal or dismisses open dropdowns.
- `1` through `6` (Numeric Keys): Auto-advances across the 6 OTP input boxes in the MFA modal. Backspace moves focus to previous box and deletes.
- `Enter`: Submits the focused form or confirms the completed OTP.

### Mouse & Touch
- **Card Click**: Clicking anywhere within an Account Card selects that account.
- **Backdrop Dismiss**: Clicking outside the MFA modal prompts cancellation.
- **Debounced Actions**: Submit buttons ignore rapid clicks while an in-flight transfer request is pending.

---

## Accessibility Floor

- **Standards**: Strict compliance with **WCAG 2.1 Level AA**.
- **Contrast**: All text against background meets or exceeds 4.5:1. Display headers and interactive badges exceed 3:1.
- **Focus Indicators**: Every interactive element (buttons, dropdowns, cards, OTP inputs) displays a high-contrast focus ring (`2px solid {colors.primary}`) with a 2px offset.
- **Screen Reader Announcements (`aria-live`)**:
  - Balance updates announce via `aria-live="polite"`: *"Primary Checking balance updated to $1,000.00"*.
  - Toast notifications and inline transfer confirmations announce automatically.
  - MFA modal is marked with `role="dialog"`, `aria-modal="true"`, and `aria-labelledby="mfa-dialog-title"`. Focus is trapped inside the dialog while active.
- **Form Semantics**: All inputs have persistent `<label>` tags associated via `htmlFor`. Error messages link to their inputs via `aria-describedby` and `aria-invalid="true"`.

---

## Key Flows

### Flow 1: Morning Balance and Position Review (UJ-1)
- **Protagonist**: Alex Morgan, reviewing personal cash distribution across accounts.
- **Steps**:
  1. Alex opens Shift Bank in a desktop browser.
  2. The application loads the Dashboard with Alex Morgan pre-authenticated.
  3. Alex views three account cards: Primary Checking ($2,500.00), High-Yield Savings ($12,450.75), and Emergency Reserve ($5,000.00).
  4. Alex clicks the `High-Yield Savings` account card.
- **Climax Beat**: The Movement Ledger panel updates to show High-Yield Savings transactions (3 pre-seeded entries), with running balances culminating in $12,450.75.
- **Resolution**: Alex confirms their savings balance is correct.
- **Zero-Movement Edge Case**: Alex clicks `Emergency Reserve`. The ledger displays the clean empty state container (*"No transaction history yet for this account"*), verifying FR-14 without errors.

### Flow 2: Routine Low-Value Transfer (UJ-2)
- **Protagonist**: Alex Morgan, transferring $250.00 to cover pending checking expenses.
- **Steps**:
  1. Alex selects `High-Yield Savings` as the Source Account.
  2. Alex selects `Primary Checking` as the Destination Account (the selector prevents choosing Savings).
  3. Alex types `250.00` into the Amount field. The submit button reads "Transfer Funds".
  4. Alex clicks "Transfer Funds".
  5. The button disables and shows a spinner. Because $250.00 $\le \$1,000.00$, no MFA is triggered.
- **Climax Beat**: The transfer completes in < 500ms. An emerald confirmation toast appears: *"Transfer of $250.00 to Primary Checking completed. Reference: TRF-1082."*
- **Resolution**: The Savings card balance updates to $12,200.75 and Checking updates to $2,750.00. The Movement Ledger shows a new debit on Savings and credit on Checking.

### Flow 3: Sensitive Transfer with Step-Up Mock MFA (UJ-3)
- **Protagonist**: Alex Morgan, moving $1,500.00 from Checking into Emergency Reserve.
- **Steps**:
  1. Alex selects `Primary Checking` (balance: $2,500.00) as Source and `Emergency Reserve` as Destination.
  2. Alex enters `1500.00` into the Amount field.
  3. The submit button dynamically changes text to "Verify & Transfer ($1,500.00)".
  4. Alex clicks "Verify & Transfer".
  5. The backend initiates the transfer in domain state `PENDING_MFA` and returns API status `MFA_REQUIRED`.
  6. The MFA Verification Modal opens over a blurred background. Focus lands on the first OTP cell.
  7. Alex enters mock OTP `123456`.
- **Climax Beat**: The modal displays a verifying spinner, checks the code, and transitions to a green checkmark banner: *"Transfer Verified & Executed"*.
- **Resolution**: The modal closes automatically after 1 second. Primary Checking reflects new balance $1,000.00, and Emergency Reserve reflects $6,500.00. A new debit is added to Checking and a credit to Emergency Reserve.
- **Failure Path (Invalid Code & Retry)**: Alex mistypes `999999`. The modal inputs shake, a red warning reads *"Invalid verification code. 2 attempts remaining"*, and the inputs reset for retry.

### Flow 4: Transfer Cancellation / Challenge Abandonment (UJ-4)
- **Protagonist**: Alex Morgan, initiating a $1,500.00 transfer but reconsidering during verification.
- **Steps**:
  1. The MFA modal is displayed on screen for a $1,500.00 transfer.
  2. Alex realizes they wanted to move money into Savings instead of Emergency Reserve.
  3. Alex clicks "Cancel Transfer" at the bottom of the modal.
- **Climax Beat**: The modal animates closed immediately.
- **Resolution**: A brief neutral notice reads *"Transfer cancelled. No funds were debited."* Primary Checking balance remains untouched at $2,500.00.

---

## Responsive & Platform

| Breakpoint | Target Viewports | Layout Behavior |
|---|---|---|
| **Desktop (`≥ 1024px`)** | 1024px – 1440px+ | - Top bar full width (1280px container).<br>- 3 account cards in a single row (`grid-cols-3`).<br>- Core workspace: 2-column layout (Left: Transfer Panel 40%, Right: Movement Ledger 60%).<br>- MFA modal: 460px centered modal. |
| **Tablet (`768px – 1023px`)** | iPad, Android tablets | - Top bar compact.<br>- 3 account cards stack to 2-columns (2 on top, 1 below) or horizontal swipe scroll.<br>- Core workspace stacks vertically: Transfer Panel on top, Movement Ledger below.<br>- MFA modal remains centered dialog with 24px margin. |
| **Mobile (`< 768px`)** | Smart phones (Sandbox view) | - Single-column stack.<br>- Account cards swipe horizontally or stack vertically.<br>- Transfer form and Movement Ledger full width stacked.<br>- MFA modal takes full screen as a bottom sheet. |
