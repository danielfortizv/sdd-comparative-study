## ADDED Requirements

### Requirement: Preserve MFA contract across transfer types
The system MUST preserve the inherited MFA threshold of COP 1,000,000 or more, fixed six-digit code `123456`, five-minute expiration, invalid-code retry behavior, and expiration status behavior. MFA is mandatory only for one-time internal or ACH transfers at or above COP 1,000,000 and for recurring schedule creation at or above that threshold. One-time internal and ACH transfers below COP 1,000,000 MUST remain executable without MFA after other applicable validations pass. A sensitive one-time internal or ACH transfer MUST NOT debit funds before successful MFA authorization. A sensitive recurring schedule MUST NOT become active before successful creation-time MFA; its properly authorized automatic executions MUST NOT require interactive MFA again. Current balance and transfer-limit validations MUST still apply at financial execution, and valid MFA MUST NOT override a failed validation.

#### Scenario: One-time transfers below threshold do not require MFA
- **WHEN** the user initiates a valid internal or ACH transfer below COP 1,000,000
- **THEN** the transfer proceeds through applicable balance and limit validations without an MFA challenge

#### Scenario: Sensitive ACH uses inherited MFA contract
- **WHEN** user initiates an otherwise valid ACH transfer of at least COP 1,000,000
- **THEN** it requires the existing MFA code and expiration behavior before acceptance and debit

#### Scenario: Internal transfer MFA regression
- **WHEN** user initiates and confirms a sensitive internal transfer using the existing correct code within five minutes
- **THEN** the transfer retains the existing Stage 1 confirmation behavior and executes only after authorization and current validation

### Requirement: Authorize sensitive recurring schedules at creation
Creation of a recurring schedule with an amount of COP 1,000,000 or more MUST require the inherited MFA verification during creation. The schedule MUST NOT become active until valid verification succeeds within five minutes. Successful creation-time verification authorizes automatic future executions for that schedule without another interactive MFA prompt, but does not override execution-time balance or limit checks. Financial parameters are immutable after successful creation; changed terms require a new schedule and applicable MFA.

#### Scenario: Sensitive schedule requires creation-time MFA
- **WHEN** user creates a recurring schedule for COP 1,000,000 or more
- **THEN** it remains inactive until the existing MFA code is verified within the existing expiration window

#### Scenario: Automatic execution needs no interactive MFA
- **WHEN** an MFA-authorized recurring schedule becomes due and current balance and limits pass
- **THEN** the system executes automatically without prompting the user again

#### Scenario: Schedule MFA does not bypass current limits
- **WHEN** a previously authorized schedule becomes due but its amount would exceed a current transfer limit
- **THEN** the occurrence fails without debit
