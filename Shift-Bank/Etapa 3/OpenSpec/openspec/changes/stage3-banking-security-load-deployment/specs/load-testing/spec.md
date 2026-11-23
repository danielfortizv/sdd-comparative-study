## Purpose

Define a reproducible Locust workload that measures the inherited banking application under a controlled synthetic dataset and reports observed performance and errors.

## ADDED Requirements

### Requirement: Isolated reproducible synthetic workload
The load test MUST use Locust against an isolated synthetic banking database and MUST NOT access real banking data or a developer's operational database. Each documented run MUST use 30 concurrent users, ramp at 5 users per second, and continue steady state for 60 seconds after ramp-up completes. Configured task weights MUST target 60% balance reads, 30% transaction history reads, and 10% actual internal transfers.

#### Scenario: Run uses specified load profile
- **WHEN** the documented load profile runs
- **THEN** it reaches 30 concurrent users at the specified ramp rate and measures 60 seconds of steady state after ramp-up

#### Scenario: Transfer workload makes real internal transfers
- **WHEN** a Locust transfer task is selected
- **THEN** it submits a real internal transfer through the application and validates its expected business outcome against the synthetic account state

#### Scenario: Load test cannot reach operational data
- **WHEN** the load test is configured without its isolated synthetic database
- **THEN** it refuses to run rather than targeting a non-isolated or real banking database

### Requirement: Measure observed mix and enforce thresholds
The test MUST compute the observed request distribution from recorded request counts, not infer it from configured weights. Acceptance requires balance/history read p95 strictly below 200 ms, transfer p95 strictly below 500 ms, and unexpected error rate strictly below 1%. Expected business rejections MUST be reported separately from unexpected errors and MUST NOT be hidden by excluding them without explicit classification.

#### Scenario: Observed workload meets thresholds
- **WHEN** the run completes with read p95 below 200 ms, transfer p95 below 500 ms, and unexpected errors below 1%
- **THEN** the result reports each threshold as passed based on measured request and error samples

#### Scenario: Threshold equality fails
- **WHEN** read p95 equals 200 ms, transfer p95 equals 500 ms, or unexpected error rate equals 1%
- **THEN** the corresponding strict acceptance threshold is reported as failed

#### Scenario: Configured and observed distributions differ
- **WHEN** actual request counts do not match configured task-weight proportions
- **THEN** the report presents the measured distribution and does not claim the configured weights were achieved

### Requirement: Preserve banking controls during performance testing
Load testing MUST use existing MFA, transfer limits, account-balance checks, and business validations. The test MUST NOT weaken or bypass those controls to improve measured performance; synthetic test actors and data MUST exercise the actual application paths.

#### Scenario: Sensitive transfer requires inherited MFA
- **WHEN** a synthetic transfer reaches the inherited sensitive-transfer threshold
- **THEN** it follows the existing MFA behavior and the test classifies any expected rejection or authorization step accurately

#### Scenario: Limits and balance validations remain active
- **WHEN** synthetic transfer traffic reaches a configured financial limit or insufficient balance
- **THEN** the application enforces the inherited rule and the test reports the expected business rejection separately

### Requirement: Preserve original machine-readable evidence
Every run report MUST include p50, p95, p99, throughput, request counts, observed request distribution, expected business rejections, unexpected errors, test environment and run parameters, acceptance outcomes, and a path to the original machine-readable results. Results MUST be retained without overwriting prior run evidence.

#### Scenario: Completed run emits complete evidence
- **WHEN** a load-test run finishes
- **THEN** its original machine-readable results and a report containing all required metrics and environment details are retained

#### Scenario: Incomplete evidence prevents acceptance claim
- **WHEN** a run lacks required metrics, environment information, or original results
- **THEN** it is marked incomplete and cannot be reported as having passed acceptance
