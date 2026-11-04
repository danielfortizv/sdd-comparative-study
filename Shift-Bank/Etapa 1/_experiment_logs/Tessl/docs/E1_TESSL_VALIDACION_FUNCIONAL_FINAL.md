# Tessl — Stage 1 — Final Manual Functional Validation

## 1. Experimental Identification

| Field | Value |
|---|---|
| Application | Shift Bank |
| Stage | 1 |
| SDD tool | Tessl |
| Date | November 3, 2026 |
| Evaluation | Manual browser-based functional testing |
| Source of evidence | User-confirmed test execution |
| Source code modifications | None |

## 2. Initial Application State

The application successfully displayed the authenticated mock user Alex Morgan, with two accounts:

| Account | Initial balance |
|---|---:|
| Primary Checking | USD 2,500.00 |
| Standard Savings | USD 10,000.00 |
| Total | USD 12,500.00 |

The dashboard, navigation controls, account cards, and transaction history rendered successfully.

The user confirmed that the visible interface buttons operated as expected.

## 3. Manual Transfer Validation

### Test A — Transfer Without MFA

- Source account: Primary Checking.
- Destination account: Standard Savings.
- Transfer amount: USD 1,000.00.
- Expected behavior: Successful execution without Security PIN verification.
- User-reported result: Passed.

### Test B — Transfer With MFA

- Source account: Primary Checking.
- Destination account: Standard Savings.
- Transfer amount: USD 1,000.01.
- Expected behavior: Security PIN verification required before executing the transfer.
- Test PIN: `1234`.
- User-reported result: Passed.

### Expected Final Balances

Assuming the two transfers were performed sequentially from the documented initial state:

| Account | Expected final balance |
|---|---:|
| Primary Checking | USD 499.99 |
| Standard Savings | USD 12,000.01 |
| Total | USD 12,500.00 |

The user confirmed that the application behaved as expected, including its transfer workflow.

The final numerical balances were not independently captured in a post-transfer screenshot.

## 4. Final Test Outcome

| Evaluation dimension | Result |
|---|---|
| Initial dashboard rendering | Passed |
| Initial account balances | Passed |
| Visible navigation interactions | Passed |
| Transaction history display | Passed |
| Transfer at USD 1,000.00 | Passed |
| Transfer at USD 1,000.01 | Passed |
| MFA requirement above threshold | Passed |
| Balance updates after transfer | Passed, user-reported |

No failures were reported during these manual scenarios.

Invalid PIN handling, repeated MFA failures, lockout behavior, concurrency, and mobile responsiveness were not tested manually in this checkpoint.

## 5. Relationship to Previous Measurements

The final requirements audit reported 51 of 51 requirements satisfied, based on direct post-correction checks and carried-forward audit evidence.

The latest automated test execution reported 45 passing tests.

SonarQube detected zero bugs, zero vulnerabilities, 21 code smells, and 82 minutes of technical debt. The scanner assigned A ratings for reliability, security, and maintainability.

These measurements complement the manual tests but represent separate evaluation methods.

## 6. Conclusion

Shift Bank Stage 1, implemented using Tessl, successfully completed the selected manual functional scenarios.

The application rendered correctly, displayed the expected initial banking data, executed an internal transfer without MFA at USD 1,000.00, and required MFA for a transfer of USD 1,000.01.

The user confirmed that the tested interactions worked as specified.

No source-code modifications were required during the manual validation.

This record closes the final manual functional validation checkpoint for Tessl Stage 1.