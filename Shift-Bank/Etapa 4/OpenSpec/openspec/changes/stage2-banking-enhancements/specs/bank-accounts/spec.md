## MODIFIED Requirements

### Requirement: Display accounts and balances
The system MUST allow the mock authenticated user Jane Doe (User ID `usr_101`) to view exactly two accounts: a Checking Account (`Cuenta Corriente`) and a Savings Account (`Cuenta de Ahorros`), including their current persisted balances represented in COP. The balances of 5.000.000,00 COP for Checking and 15.000.000,00 COP for Savings are initial seeded balances only. Subsequent views MUST display persisted updates resulting from completed internal transfers, accepted pending ACH debits, and refunds for failed ACH transfers.

#### Scenario: User loads dashboard initially
- **WHEN** the user views the main accounts overview before any transfers are performed
- **THEN** the system displays "Cuenta Corriente" with initial balance 5.000.000,00 COP and "Cuenta de Ahorros" with initial balance 15.000.000,00 COP

#### Scenario: User views dashboard after a completed transfer
- **WHEN** a transfer of 1.000.000,00 COP from Savings to Checking is COMPLETED and the user views the main accounts overview
- **THEN** the system displays "Cuenta Corriente" with updated balance 6.000.000,00 COP and "Cuenta de Ahorros" with updated balance 14.000.000,00 COP

#### Scenario: User views balance after ACH acceptance and failure
- **WHEN** an accepted ACH transfer debits Checking and later fails
- **THEN** the displayed persisted Checking balance reflects the debit while ACH is pending and reflects exactly one refund after it fails
