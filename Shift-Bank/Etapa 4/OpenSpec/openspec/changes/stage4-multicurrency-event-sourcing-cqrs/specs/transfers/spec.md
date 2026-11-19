## MODIFIED Requirements

### Requirement: Transfer between own accounts
The system MUST allow the user to transfer a positive two-decimal amount between their own accounts only when source and destination currencies match. A committed transfer MUST debit and credit the same amount atomically, preserve the account currencies, and appear in currency-explicit history. Cross-currency movement MUST use `/api/conversions` exclusively.

#### Scenario: Successful transfer under sensitive limit
- **WHEN** the user submits a valid USD transfer between CHK-1001 and SAV-2001 with the required idempotency key and expected versions
- **THEN** the source is debited and destination credited atomically, both balances remain USD, and one completed transfer is recorded

#### Scenario: Cross-currency internal transfer is rejected
- **WHEN** the source and destination accounts have different currencies
- **THEN** the request is rejected without balance, version, projection, or successful-transfer mutation and directs the user to the conversion operation

#### Scenario: Transfer validation preserves inherited safeguards
- **WHEN** the user requests a self-transfer, non-positive amount, amount with unsupported precision, or amount above available funds
- **THEN** the request is rejected without a partial debit or credit and its failure is auditable
