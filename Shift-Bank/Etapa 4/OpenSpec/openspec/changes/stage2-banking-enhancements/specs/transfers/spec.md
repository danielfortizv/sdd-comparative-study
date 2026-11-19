## MODIFIED Requirements

### Requirement: Transfer between own accounts
The system MUST allow the user to transfer funds between their two owned accounts (Checking and Savings) using decimal-safe COP amounts with no more than two decimal places. Transfers MUST enforce current per-transfer and UTC daily limits. An internal transfer amount contributes once to daily usage, not once per debit and credit. The backend MUST ensure an accepted transfer cannot make the source balance negative.

#### Scenario: Successful transfer under sensitive limit
- **WHEN** user requests a permitted transfer of 150.000,00 COP from Checking to Savings
- **THEN** the system immediately debits 150.000,00 COP from Checking, credits 150.000,00 COP to Savings, and marks the transfer as COMPLETED

#### Scenario: Transfer at per-transfer and daily limit boundaries
- **WHEN** an internal transfer equals the per-transfer limit and makes daily usage equal to, but not greater than, the daily limit
- **THEN** the system permits the transfer if balance and other checks pass and counts the amount once

### Requirement: Validate transfers and reject invalid requests
The system MUST validate internal transfer requests and reject self-transfers, non-positive amounts, amounts with more than two decimal places, amounts exceeding available source funds, and transfers exceeding current per-transfer or UTC daily limits. Backend validation is authoritative and MUST precede any debit. A valid MFA code MUST NOT override a failed balance or limit check.

#### Scenario: Transfer to same account is rejected
- **WHEN** user requests a transfer with Checking as both source and destination
- **THEN** the system rejects the request and indicates self-transfer is forbidden

#### Scenario: Transfer with negative amount is rejected
- **WHEN** user requests an internal transfer with an amount of -50.000,00 COP
- **THEN** the system rejects the request with an error indicating that the amount must be positive and without changing account balances

#### Scenario: Transfer with zero amount or unsupported precision is rejected
- **WHEN** user requests an internal transfer with a zero amount or more than two decimal places
- **THEN** the system rejects the request without changing account balances

#### Scenario: Transfer with insufficient funds is rejected
- **WHEN** the configured per-transfer limit permits COP 6.000.000,00 and sufficient daily allowance remains, but the user requests that amount from Checking which contains only COP 5.000.000,00
- **THEN** the system rejects the request specifically for insufficient funds and does not modify either account balance

#### Scenario: Transfer exceeding limits is rejected
- **WHEN** user requests an otherwise valid transfer exceeding either current transfer limit
- **THEN** the backend rejects it without debit, even if the user can provide a valid MFA code

### Requirement: Source balance revalidation on confirmation
The system MUST re-evaluate the source account's available balance at the exact moment an internal transfer is executed or MFA is confirmed, and MUST revalidate applicable transfer limits before completion. If a check fails, the system rejects execution without a debit and records a FAILED pending transfer where applicable.

#### Scenario: Balance depleted during pending MFA
- **WHEN** user confirms a pending transfer of 1.500.000,00 COP, but a separate transfer has depleted the source account below 1.500.000,00 COP
- **THEN** the system rejects confirmation and marks the transfer FAILED due to insufficient funds

#### Scenario: Limit usage changes during pending MFA
- **WHEN** a pending transfer is confirmed after other transfers have consumed its remaining daily allowance
- **THEN** the system rejects confirmation without a debit, regardless of a valid MFA code
