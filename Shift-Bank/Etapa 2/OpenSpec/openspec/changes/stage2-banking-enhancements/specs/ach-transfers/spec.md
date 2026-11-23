## Purpose

Enables the mock user to send simulated external ACH transfers to saved or ad hoc recipients while retaining auditable, reliable transfer outcomes.

## ADDED Requirements

### Requirement: Manage user-owned beneficiaries
The system MUST allow the authenticated mock user to create, list, update, and delete saved beneficiaries through the application interface. A beneficiary MUST include a name, bank name, a routing number of exactly nine numeric digits, and an account number of four to seventeen numeric digits. Beneficiary changes MUST NOT alter recipient information already captured by an accepted ACH transfer or recurring ACH schedule.

#### Scenario: Create and list beneficiary
- **WHEN** the user saves a beneficiary with valid required fields
- **THEN** the beneficiary is associated with the current mock user and appears in that user's beneficiary list

#### Scenario: Identify invalid routing number while typing
- **WHEN** the user enters a routing number that is not exactly nine numeric digits
- **THEN** the interface identifies the routing-number error while the user types, blocks submission, and the system does not save invalid beneficiary data

#### Scenario: Reject invalid account number
- **WHEN** the user enters an account number containing non-digits or outside four to seventeen digits
- **THEN** the interface identifies the account-number error, blocks submission, and the system does not save invalid beneficiary data

#### Scenario: Update or delete saved beneficiary
- **WHEN** the user updates or deletes a saved beneficiary
- **THEN** the change applies to future recipient selection and previously accepted transfers and schedules retain their captured recipient details

#### Scenario: Manage beneficiaries in the application
- **WHEN** the user opens beneficiary management
- **THEN** the interface allows them to list, create, update, and delete saved beneficiaries and displays validation errors for rejected details

### Requirement: Submit simulated ACH transfer
The system MUST allow the user to transfer a positive amount with no more than two decimal places from an existing owned source account to either a saved beneficiary or a valid ad hoc external recipient. Every external recipient, whether saved or ad hoc, MUST include beneficiary name, bank name, a routing number of exactly nine numeric digits, and an account number of four to seventeen numeric digits. The backend MUST validate recipient data, source account, available balance, per-transfer limit, and UTC daily limit before acceptance. The interface MUST clearly distinguish internal transfers from external ACH transfers, allow selecting or entering a recipient, offer optional beneficiary saving, validate routing number format while typing, and block invalid submission. The system MUST NOT connect to an actual bank, ACH network, or payment provider.

#### Scenario: Submit valid ad hoc recipient transfer
- **WHEN** the user submits a valid ACH transfer to an ad hoc recipient and all balance, limit, and authorization checks pass
- **THEN** the system accepts the transfer and records the external recipient details used for the transfer

#### Scenario: Use saved beneficiary
- **WHEN** the user selects one of their saved beneficiaries for a valid ACH transfer
- **THEN** the accepted transfer uses and preserves that beneficiary's recipient details

#### Scenario: Submit non-sensitive ACH without MFA
- **WHEN** the user submits an otherwise valid ACH transfer below COP 1,000,000
- **THEN** the system accepts it into `pending` and debits the source once without requesting MFA

#### Scenario: Reject invalid amount or recipient
- **WHEN** an ACH request has a non-positive amount, more than two decimal places, invalid routing or account number, or invalid recipient details
- **THEN** the backend rejects the request before acceptance, the interface displays an understandable validation error, and the source account is not debited

#### Scenario: Reject missing source or insufficient funds
- **WHEN** an ACH request names a nonexistent source account or exceeds the source's available balance
- **THEN** the system rejects the request, displays an understandable error, and creates no ACH debit or accepted pending transfer

### Requirement: Authorize and accept sensitive ACH transfers
An ACH transfer of COP 1,000,000 or more MUST use the inherited MFA threshold, fixed code, retry behavior, and five-minute expiration behavior. It MUST remain in `PENDING_MFA` until successful authorization and become `EXPIRED` when the inherited window expires without successful verification. Funds MUST NOT be debited before successful MFA authorization. The transfer MUST pass applicable balance and transfer-limit checks before MFA authorization is completed; valid MFA MUST NOT override a failed validation. After successful authorization and acceptance, the ACH transfer MUST enter `pending` and debit the source account immediately.

#### Scenario: Sensitive ACH awaits MFA without debit
- **WHEN** the user submits an otherwise valid ACH transfer of at least COP 1,000,000
- **THEN** the transfer awaits the inherited MFA confirmation and the source balance remains unchanged until valid authorization

#### Scenario: Correct MFA accepts sensitive ACH
- **WHEN** the user confirms the pending sensitive ACH transfer within five minutes using code `123456` and current validations still pass
- **THEN** the ACH transfer enters `pending` and the source account is debited exactly once

#### Scenario: Invalid or expired MFA does not debit
- **WHEN** the user submits an incorrect code or confirms after the inherited five-minute expiration
- **THEN** the transfer is not accepted as pending and the source account is not debited

#### Scenario: Incorrect MFA code can be retried
- **WHEN** the user enters an incorrect code for a sensitive ACH transfer before the five-minute expiry
- **THEN** the transfer remains pending MFA without a debit and the user may retry with the correct code before expiry

#### Scenario: Sensitive ACH MFA expires
- **WHEN** five minutes pass after a sensitive ACH request without successful verification
- **THEN** its MFA state becomes `EXPIRED` and the source account remains unchanged

#### Scenario: MFA cannot bypass transfer limits
- **WHEN** a sensitive ACH transfer would exceed either current transfer limit
- **THEN** the backend rejects it and a valid MFA code cannot cause acceptance or debit

### Requirement: Settle or fail accepted ACH transfers idempotently
An accepted ACH transfer MUST enter `pending`, immediately debit its source once without making the source balance negative, and under normal simulation conditions automatically transition to `settled` after 30 seconds with a settlement timestamp. Settlement MUST NOT debit again. The system MUST NOT introduce random ACH failures. A controlled internal simulation or testing mechanism MUST permit deterministic, reproducible failures without an unrestricted public failure endpoint. A failed accepted transfer MUST transition to `failed`, preserve a machine-readable failure reason and comprehensible user-facing explanation, and refund exactly the originally debited amount once. State transitions and monetary effects MUST remain consistent and idempotent across repeated processing and application restarts. Accepted-transfer history and captured recipient information MUST remain available through settlement or failure.

#### Scenario: Normal ACH settlement
- **WHEN** an accepted pending ACH transfer reaches 30 seconds under normal simulation conditions
- **THEN** it transitions to `settled`, records a settlement timestamp, and does not debit the source again

#### Scenario: Controlled ACH failure refunds once
- **WHEN** the controlled simulation selects failure as an accepted pending ACH transfer reaches settlement processing after the 30-second delay
- **THEN** it transitions to `failed`, preserves a machine-readable reason and understandable explanation in history, and restores exactly the original debit once

#### Scenario: Repeat processing has no duplicate effect
- **WHEN** a pending ACH transfer is processed more than once or processing resumes after restart
- **THEN** the transfer has at most one settlement or failure transition and at most one debit or refund

#### Scenario: Concurrent transfers cannot overdraw source
- **WHEN** concurrent ACH requests compete for more funds than the source account contains
- **THEN** the system accepts only transfers covered by available funds and no accepted debit makes the account balance negative

### Requirement: Display ACH status and recipient history
The system MUST show ACH transfer recipient details and current `pending`, `settled`, or `failed` status in transaction history, including failure reason when failed. Historical recipient details MUST remain those used when the transfer was accepted.

#### Scenario: View pending and settled ACH history
- **WHEN** the user views history for a pending or settled ACH transfer
- **THEN** the interface distinguishes it from an internal transfer and displays its external recipient and status

#### Scenario: View failed ACH history
- **WHEN** an ACH transfer fails
- **THEN** its history entry remains visible with recipient details, failed status, and understandable failure reason
