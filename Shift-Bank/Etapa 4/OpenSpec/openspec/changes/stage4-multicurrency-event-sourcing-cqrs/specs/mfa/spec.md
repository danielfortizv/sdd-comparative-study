## MODIFIED Requirements

### Requirement: Sensitive transfers threshold
The system MUST require mock MFA for an eligible financial operation if and only if its exact, unrounded USD equivalent is greater than USD 1,000.00. The rule MUST apply to internal transfers, conversions, ACH, and recurring execution or authorization as defined by the operation lifecycle. A request awaiting MFA MUST NOT apply its financial effect before successful confirmation. The existing six-digit mock code 123456, five-minute expiration, and retry behavior MUST remain intact.

#### Scenario: Operation exactly at the unrounded threshold
- **WHEN** an operation's unrounded USD equivalent is exactly USD 1,000.00
- **THEN** the operation does not require MFA because the D-07 comparison is strictly greater than the threshold

#### Scenario: Sensitive transfer initiated
- **WHEN** an operation's unrounded USD equivalent is greater than USD 1,000.00
- **THEN** it enters PENDING_MFA and applies no debit, credit, conversion, or recurring occurrence until authorized

#### Scenario: Confirmation retains inherited mock-code and expiry behavior
- **WHEN** the user confirms a pending operation within five minutes with code 123456
- **THEN** the operation proceeds subject to current balance, limit, version, and currency validation; an invalid code leaves it pending, and an expired request becomes EXPIRED without a financial effect
