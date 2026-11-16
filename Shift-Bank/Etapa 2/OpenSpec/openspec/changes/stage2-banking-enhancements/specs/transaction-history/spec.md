## MODIFIED Requirements

### Requirement: Chronological ledger of movements
The system MUST record and make queryable chronological history for internal transfers, ACH transfers, and recurring payment executions. Existing transaction fields MUST remain available for internal transfers. ACH entries MUST include the external recipient information used at acceptance, transfer status, settlement timestamp when settled, and understandable failure reason when failed. Recurring executions MUST be individually distinguishable and linked to their schedule and occurrence. The history MUST show relevant pending, settled, and failed ACH states as well as existing internal statuses.

#### Scenario: User views transaction history
- **WHEN** user requests transaction history
- **THEN** the system returns a chronological list including seeded history, new internal transfers, ACH transfers, and recurring executions

#### Scenario: User views ACH lifecycle history
- **WHEN** an ACH transfer is pending, settled, or failed
- **THEN** history displays its external recipient details and current status, plus settlement time or failure reason when applicable

#### Scenario: User views recurring execution history
- **WHEN** a recurring occurrence has been attempted
- **THEN** history displays that individual execution outcome and identifies its schedule

### Requirement: Show both incoming and outgoing movements for each account
The system MUST retrieve and filter transaction history so that viewing an individual owned account shows all internal movements where the account was source or destination, plus external ACH debits and recurring executions sourced from that account. External recipients MUST NOT be represented as credits to an owned account.

#### Scenario: User filters movements for Checking account
- **WHEN** user views movements specifically for Checking (`Cuenta Corriente`)
- **THEN** the system displays all internal transactions where Checking is source OR destination and all ACH or recurring executions debited from Checking

#### Scenario: User views recurring execution failure
- **WHEN** a recurring execution fails without a debit
- **THEN** the execution outcome is visible in history without presenting it as a completed balance movement
