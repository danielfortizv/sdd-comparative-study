## Manual Functional Validation

Manual browser validation was performed after the implementation and compliance review.

### Overall result

The implemented Shift Bank application successfully supported the expected Stage 1 scenarios, including:

- Initial Checking and Savings balances.
- Direct transfers below the MFA threshold.
- Historical transaction display.
- User-facing account names without internal identifiers.
- MFA activation for sensitive transfers.
- MFA incorrect-code retry.
- MFA successful confirmation.
- MFA expiration behavior.
- Insufficient-funds validation.
- Balance updates and transaction history behavior.

### Observed limitation — MFA cancellation

When a sensitive transfer is in `PENDING_MFA` and the user selects Cancel/Close:

- The MFA dialog closes.
- The pending transfer is no longer available to resume.
- The user must initiate a new transfer if they want to continue.
- No "Pending Sensitive Transfers" resume mechanism is present.

This behavior was observed during manual validation.

At this point it is **not classified as an implementation defect**, because the approved Kiro requirements and design must first be checked to determine whether preserving a pending transfer after cancellation and providing a resume mechanism were explicitly required.

No corrective implementation was performed during manual validation.

### MFA Cancellation Traceability Result

The absence of a Resume mechanism after cancelling the MFA dialog was reviewed against the approved Kiro requirements, design, and tasks.

The behavior is not explicitly required by any approved artifact. Therefore, it is recorded as an observed implementation characteristic rather than a failed acceptance criterion.

Classification: `NO CORRECTION REQUIRED`.

## Manual Functional Validation — Final Results

All manual validation scenarios were executed through the browser.

### Scenario 5 — MFA Expiration

A sensitive transfer was created and left pending until the five-minute countdown reached zero.

Observed behavior:

- The MFA code input became disabled once the timer reached zero.
- The Confirm button also became disabled.
- The user could only select Cancel.
- Selecting Cancel closed/finalized the pending interaction in the UI.
- No transfer confirmation occurred after expiration.
- No balance update occurred as a result of the expired MFA attempt.

Result: PASS

The observed UI behavior prevents the user from submitting an MFA code after the expiration window.

### Scenario 6 — Insufficient Funds

An insufficient-funds transfer scenario was executed.

Observed behavior:

- The application displayed a red error message indicating insufficient funds.
- The transfer was not completed.
- No account balance was modified.

Result: PASS

The application correctly prevents the transfer when available funds are insufficient and preserves the existing balances.

### Final Manual Validation Result

All planned manual functional scenarios for Kiro were executed.

Main functionality validated:

- Initial account balances
- Direct transfers below the MFA threshold
- Historical transaction history
- Friendly account names
- Internal-ID masking
- MFA activation
- Incorrect MFA code
- MFA retry
- MFA cancellation behavior
- MFA resume behavior as defined by Kiro's approved scope
- Successful MFA confirmation
- MFA expiration
- Insufficient funds
- Preservation of balances when transfers fail

No application source code was modified during manual validation.