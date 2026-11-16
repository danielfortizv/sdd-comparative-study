## Purpose

Lets the mock user authorize, manage, and inspect recurring internal or ACH payments whose executions are reliable and subject to current banking rules.

## ADDED Requirements

### Requirement: Create recurring payment schedule
The system MUST allow the user to create recurring internal or ACH payments with an existing source account, valid destination or recipient, and positive amount with no more than two decimal places. Supported frequencies MUST be daily, weekly, and monthly, defined exactly as intervals of 1, 7, and 30 days. A future date without an explicit time represents 00:00 UTC and MUST resolve to a timestamp strictly later than schedule creation. Without a start date, the first execution MUST occur after one full interval measured from creation and never immediately. The first scheduled timestamp MUST establish a persistent UTC cadence anchor, and subsequent occurrences MUST use that original anchor without accumulating scheduling drift. A successfully created schedule starts `active`.

#### Scenario: Create schedule with future start
- **WHEN** the user creates a valid schedule with a future start date
- **THEN** it starts `active` and the first execution is scheduled for that date

#### Scenario: Create schedule without start date
- **WHEN** the user creates a valid schedule without a start date
- **THEN** the first execution is scheduled one full frequency interval after creation

#### Scenario: Apply exact frequency intervals
- **WHEN** the user selects daily, weekly, or monthly frequency
- **THEN** the schedule uses exactly 1, 7, or 30 days respectively between anchored occurrences

#### Scenario: Non-sensitive schedule does not require MFA
- **WHEN** the user creates a valid recurring schedule for less than COP 1,000,000
- **THEN** it becomes active through normal creation without an MFA challenge

#### Scenario: Future start date resolves to UTC midnight
- **WHEN** the user selects a future start date without a time
- **THEN** the first execution is scheduled at 00:00 UTC on that date and its timestamp is strictly later than creation

#### Scenario: Reject start date that is not in the future
- **WHEN** the selected date resolves to 00:00 UTC at or before schedule creation
- **THEN** the system rejects the schedule date and does not activate the schedule

#### Scenario: Repeated occurrences retain original cadence anchor
- **WHEN** a schedule advances through multiple daily, weekly, or 30-day intervals
- **THEN** each occurrence is calculated from the first scheduled timestamp and does not drift from accumulated processing delays

#### Scenario: Reject invalid schedule
- **WHEN** a schedule has invalid source, destination or recipient, non-positive amount, or unsupported monetary precision
- **THEN** the system rejects creation and does not create an active schedule

### Requirement: Authorize sensitive recurring schedule at creation
A recurring schedule whose amount is COP 1,000,000 or more MUST complete the inherited MFA flow during creation. It MUST remain in `PENDING_MFA` until successful verification and become `EXPIRED` if the inherited five-minute window expires without successful verification. The schedule MUST NOT become active until successful MFA using the existing fixed code. Before activation, the backend MUST revalidate the current per-transfer limit against the scheduled amount; daily usage is evaluated when each occurrence is due. Successful authorization applies to future automatic executions of that immutable schedule; executions MUST NOT prompt for interactive MFA again. MFA authorization MUST NOT override current balance or transfer limits.

#### Scenario: Sensitive schedule awaits MFA
- **WHEN** the user creates a valid recurring schedule with an amount of at least COP 1,000,000
- **THEN** it remains inactive pending MFA confirmation and no transfer is executed

#### Scenario: Successful MFA activates schedule
- **WHEN** the user confirms creation with code `123456` within five minutes
- **THEN** the schedule becomes `active` and its first execution remains at the defined scheduled date

#### Scenario: Failed or expired MFA does not activate
- **WHEN** the user provides an invalid code or the MFA window expires
- **THEN** an invalid code leaves the schedule in `PENDING_MFA` for retry, while expiration transitions it to `EXPIRED`; neither outcome activates the schedule or executes a payment

#### Scenario: Current per-transfer limit is revalidated at schedule authorization
- **WHEN** the per-transfer limit is reduced below a sensitive schedule's amount while its MFA confirmation is pending
- **THEN** a valid code does not activate the schedule

#### Scenario: MFA confirmation after first execution time is rejected
- **WHEN** the user confirms MFA for a sensitive schedule at or after its originally requested first execution timestamp
- **THEN** the system rejects activation, leaves no executable schedule or financial transfer, displays that the first execution time has passed and a new schedule with a valid future start time is required, and safely discards or retains the pending draft only as non-executable

### Requirement: Manage schedule states and immutable terms
The system MUST allow an active schedule to be paused, an active or paused schedule to be cancelled, and a paused schedule to be resumed. A cancelled schedule is terminal and MUST NOT be reactivated. Amount, source account, destination or ACH recipient, transfer type, and frequency MUST remain immutable after successful creation; changing them requires cancellation and creation of a new schedule with normal MFA authorization when applicable. Pause and resume MUST NOT reset cadence or require new MFA. Paused and cancelled schedules MUST NOT execute.

#### Scenario: Pause prevents execution
- **WHEN** an active schedule is paused before an occurrence is processed
- **THEN** it does not execute while paused

#### Scenario: Resume preserves cadence and skips missed occurrences
- **WHEN** a paused schedule is resumed after one or more original-cadence occurrences have passed
- **THEN** missed occurrences are skipped and the next execution is the first future occurrence on the original cadence

#### Scenario: Cancel is terminal
- **WHEN** the user cancels an active or paused schedule and later attempts to resume it
- **THEN** the schedule remains cancelled and never executes

#### Scenario: Financial terms cannot be edited
- **WHEN** the user attempts to change an immutable schedule term
- **THEN** the change is rejected and the user must create a new schedule to use different terms

### Requirement: Execute due occurrences with current validations
The system MUST automatically execute due active schedule occurrences. Each occurrence MUST revalidate current available source balance, per-transfer limit, and UTC daily limit. Internal transfers count once toward daily usage; ACH occurrences follow the ACH pending debit and settlement lifecycle. An occurrence that fails due to insufficient funds or exceeded limits MUST be recorded without a debit, and the schedule MUST advance to its next cadence occurrence.

#### Scenario: Due internal occurrence succeeds
- **WHEN** an active internal schedule becomes due and current balance and limits permit it
- **THEN** one internal transfer executes and contributes its amount once to daily usage

#### Scenario: Due ACH occurrence is accepted
- **WHEN** an active ACH schedule becomes due and current balance and limits permit it
- **THEN** one ACH transfer enters the approved pending lifecycle and the schedule advances independently

#### Scenario: Due occurrence fails current balance or limit check
- **WHEN** a due occurrence has insufficient available funds or would exceed a current transfer limit
- **THEN** the failed execution is recorded without a debit and the schedule remains able to reach its next occurrence

### Requirement: Recover schedules and occurrences safely
Schedules and occurrence processing state MUST survive application restarts. The system MUST use a stable logical identity for each scheduled occurrence and MUST prevent duplicate monetary effects if processing is repeated. Occurrences missed while the application is offline MUST be skipped without debit or limit usage. After restart, the next execution MUST be the first future occurrence on the original cadence. A previously accepted or partially processed occurrence MUST be recovered consistently and MUST NOT be classified as skipped merely because of restart.

#### Scenario: Restart skips missed due occurrences
- **WHEN** the application restarts after one or more occurrence dates passed while offline
- **THEN** those occurrences are skipped and the next future original-cadence occurrence remains scheduled

#### Scenario: Restart recovers accepted occurrence
- **WHEN** the application restarts while an occurrence has already been accepted or partially processed
- **THEN** it recovers that occurrence's state without misclassifying it as skipped or repeating its monetary effect

#### Scenario: Reprocessing occurrence is idempotent
- **WHEN** the scheduler attempts the same occurrence more than once
- **THEN** no duplicate internal transfer, ACH debit, settlement, or refund is produced

### Requirement: Display recurring schedules and executions
The system MUST let the user view schedules, their active, paused, or cancelled status, next execution timestamp, and recorded execution outcomes including failures and their reasons. The interface MUST display the timezone as UTC, clearly communicate scheduled execution time, distinguish a failed occurrence from the schedule's status, display backend validation or execution errors in understandable terms, and provide the creation-time MFA confirmation flow when required.

#### Scenario: View schedule and next execution
- **WHEN** the user views recurring payments
- **THEN** each schedule displays its status, transfer details, frequency, and upcoming execution date

#### Scenario: View UTC execution time
- **WHEN** the user views a schedule's next execution
- **THEN** the interface displays the scheduled time and explicitly identifies UTC as its timezone

#### Scenario: View schedule validation error
- **WHEN** schedule creation or a schedule operation is rejected by backend validation
- **THEN** the interface displays an understandable error and does not show the rejected operation as successful

#### Scenario: View recurring execution failure reason
- **WHEN** a recurring execution fails due to current balance or transfer limits
- **THEN** the interface displays the recorded failure reason separately from the schedule status

#### Scenario: View failed occurrence on active schedule
- **WHEN** an execution fails and a later occurrence remains scheduled
- **THEN** the failure is visible as an execution result while the schedule remains active with its next execution date
