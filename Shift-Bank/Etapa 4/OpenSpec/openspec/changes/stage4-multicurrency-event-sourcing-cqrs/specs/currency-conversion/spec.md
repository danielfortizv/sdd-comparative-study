## Purpose

Defines exact, auditable currency arithmetic and simulated exchange behavior for the supported USD, EUR, and GBP account currencies.

## ADDED Requirements

### Requirement: Exact financial representation
The system MUST represent backend financial amounts with decimal-safe arithmetic and frontend financial amounts with integer minor units. API monetary values MUST be strings with exactly two fractional digits. Financial calculations MUST NOT use binary floating point, fees, or intermediate rounding; the final amount MUST be rounded once with ROUND_HALF_UP.

#### Scenario: Monetary input and output precision
- **WHEN** a valid amount is submitted and returned by an account or operation API
- **THEN** it is validated to two decimal places and serialized as a two-decimal string without a binary floating-point calculation

#### Scenario: Final half-up rounding
- **WHEN** a rational conversion produces a final result exactly halfway between two cents
- **THEN** the final amount is rounded once using ROUND_HALF_UP and the same vector yields the same result in backend and frontend arithmetic

### Requirement: Fixed simulated FX conversions
The system MUST provide cross-currency movement exclusively through `/api/conversions` using these exact rational rates: USD→EUR 9/10; USD→GBP 8/10; EUR→USD 10/9; GBP→USD 10/8; EUR→GBP 8/9; GBP→EUR 9/8. Each conversion MUST identify the source and destination accounts, currencies, amounts, applied rate, operation ID, and resulting transaction records. The source debit and destination credit MUST be atomic, and no fee may be charged.

#### Scenario: All approved rate directions are applied exactly
- **WHEN** a conversion is requested for any of the six approved currency directions
- **THEN** the system applies the corresponding rational rate, rounds only the final destination amount, records both currency amounts and the rate, and creates no fee entry

#### Scenario: Approved conversion vectors
- **WHEN** the system converts USD 100.00 to EUR, USD 100.00 to GBP, EUR 90.00 to USD, GBP 80.00 to USD, EUR 90.00 to GBP, or GBP 80.00 to EUR
- **THEN** the respective results are EUR 90.00, GBP 80.00, USD 100.00, USD 100.00, GBP 80.00, and EUR 90.00

#### Scenario: Conversion cannot partially commit
- **WHEN** the source debit, destination credit, event, projection, audit, or idempotency persistence fails
- **THEN** no partial conversion is committed or reported successful

#### Scenario: Unsupported rate or same-currency conversion
- **WHEN** a conversion uses an unsupported currency pair or identical source and destination currency
- **THEN** the system rejects it without a financial effect

#### Scenario: Small conversion rounds only at final output
- **WHEN** USD 0.05 is converted to EUR at 9/10
- **THEN** the final EUR amount is EUR 0.05 under ROUND_HALF_UP with no intermediate rounding
