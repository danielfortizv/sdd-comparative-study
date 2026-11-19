## MODIFIED Requirements

### Requirement: Display accounts and balances
The system MUST allow mock authenticated user Jane Doe (`usr_101`) to view four active accounts, each with exactly one explicit currency from USD, EUR, or GBP. For the reported inherited initialization state, the public checking account `CHK-1001` MUST have USD 1,250.00 and preserve internal identifier `acc_checking`; public savings `SAV-2001` MUST have USD 3,750.00 and preserve internal identifier `acc_savings`. The new `EUR-3001` EUR account and `GBP-4001` GBP account MUST each start at 0.00. The USD values are the approved one-time 4,000 COP/USD migration result and explicitly deviate from common D-02 reference amounts USD 2,500.00 and USD 10,000.00. The system MUST NOT add balancing transactions. Account responses MUST identify currency and expose canonical public references while retaining legacy identifiers as accepted compatibility aliases. Subsequent views MUST show committed balances.

#### Scenario: User loads dashboard initially
- **WHEN** the user views the accounts after migrating the reported inherited initialization state
- **THEN** the system returns CHK-1001 USD 1,250.00, SAV-2001 USD 3,750.00, EUR-3001 EUR 0.00, and GBP-4001 GBP 0.00 with explicit currency and legacy aliases for the two inherited accounts

#### Scenario: User views dashboard after a completed transfer
- **WHEN** a valid USD transfer completes from CHK-1001 to SAV-2001
- **THEN** the next account view reflects the debit and credit in USD without changing either account's currency

#### Scenario: Unsupported or ambiguous currency is rejected
- **WHEN** an account or balance state has no approved USD, EUR, or GBP currency mapping
- **THEN** the system fails closed and does not expose or mutate that state as a spendable Stage 4 account
