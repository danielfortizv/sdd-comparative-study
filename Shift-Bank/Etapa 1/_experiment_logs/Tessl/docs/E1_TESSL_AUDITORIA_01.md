# Tessl — Stage 1 — Post-Implementation Audit

## 1. Audit Identification

- Case study: Shift Bank.
- Stage: 1 — Initialization.
- Evaluation tool: Tessl CLI 0.118.1.
- SDD plugin: `tessl-labs/spec-driven-development@2.0.1`.
- Agent: Gemini CLI 0.65.0.
- Model displayed during implementation: `gemini-3.5-flash`; underlying invocation not independently verified.
- Audit date: November 1, 2026.
- Audit type: Read-only specification-to-implementation analysis.
- Source of evidence: Gemini CLI post-implementation audit transcript.

The experimental methodology specified Gemini CLI 0.60.0. The audit confirmed that version 0.65.0 remained installed. This deviation must be considered when comparing tools.

## 2. Specification Metrics

Four project-authored specification files were identified.

| Specification | Lines | Characters | Bytes |
|---|---:|---:|---:|
| accounts.spec.md | 53 | 2,232 | 2,285 |
| transfers.spec.md | 72 | 3,227 | 3,299 |
| transactions.spec.md | 53 | 2,361 | 2,414 |
| mfa.spec.md | 57 | 2,596 | 2,653 |
| **Total** | **235** | **10,416** | **10,651** |

- Specification files: 4.
- Average density: 58.75 lines/file.
- Minimum: 53 lines.
- Q1: 53 lines.
- Median: 55 lines.
- Q3: 60.75 lines.
- Maximum: 72 lines.

Quartiles were calculated using NumPy's default linear interpolation.

Only `specs/*.spec.md` files were included. Generated Tessl skills, agent configuration, researcher documentation, and dependencies were excluded.

## 3. Requirements and Traceability

The Gemini audit identified 51 individually testable requirements.

| Specification | Requirements |
|---|---:|
| Accounts | 11 |
| Transfers | 16 |
| Transactions | 10 |
| MFA | 14 |
| **Total** | **51** |

The agent classified 45 requirements as functional and 6 as non-functional.

### Reported Satisfaction

| Status | Count | Percentage |
|---|---:|---:|
| Satisfied | 50 | 98.04% |
| Partially satisfied | 1 | 1.96% |
| Not satisfied | 0 | 0% |
| Not verifiable | 0 | 0% |

These results represent the agent's static audit classification, not independently verified functional coverage.

### Identified Specification Discrepancy

Requirement `TRF-06` in `specs/transfers.spec.md` requires HTTP 428 with the response:

```json
{
  "detail": "MFA_REQUIRED",
  "message": "Security PIN required for transfers over $1,000"
}
```

The backend implementation in `backend/app/services/transfer_service.py` returns:

```json
{
  "detail": "MFA_REQUIRED"
}
```

The required `message` field is missing.

Classification: Partially Satisfied.

## 4. Source Code Metrics

| Component | Files | Lines |
|---|---:|---:|
| Backend production Python | 14 | 663 |
| Frontend production TypeScript/TSX | 9 | 1,046 |
| Frontend CSS | 1 | 820 |
| **Total production source** | **24** | **2,529** |

Additionally, `frontend/vite.config.ts` contains 21 lines and was excluded from the production LOC total.

### Test Code

| Component | Lines |
|---|---:|
| Backend test code | 371 |
| Frontend test code | 561 |
| **Total** | **932** |

Line counts include blank lines and comments. Test code was excluded from production LOC.

### Derived Indicators

- Code/specification ratio: 2,529 / 235 = 10.76.
- Requirement density: 51 / 235 × 100 = 21.70 requirements per 100 specification lines.
- Findings per KLOC: pending SonarQube analysis.
- Code coverage: not measured.

## 5. Automated Testing

- Backend: 19 Pytest tests collected.
- Frontend: 21 Vitest tests passed.
- Total existing automated tests: 40.
- Previously reported implementation validation: 19 backend and 21 frontend tests passed.
- Total reported test pass rate: 100%.

Passing tests do not establish complete requirement coverage.

## 6. Technical Findings

### Financial Precision

Monetary fields use Python floating-point values and SQLAlchemy Float columns. The transfer service applies two-decimal rounding.

This can introduce numerical precision limitations compared with fixed-point decimal or integer-cent representations.

### Transaction Atomicity

The transfer implementation updates both account balances, creates the transfer record, and creates two ledger movements in one SQLAlchemy session followed by a single commit.

The audit identified the absence of explicit rollback handling around the operation.

### MFA Boundary Testing

The specification defines the sensitive-transfer threshold as strictly greater than USD 1,000.

The implementation uses this comparison, but the automated tests do not explicitly exercise the boundary values USD 1,000.00 and USD 1,000.01.

### Additional Testing Gaps

- Concurrent transfers against the same source account.
- Frontend integration behavior when the API returns HTTP 428.

These remain verification gaps, not confirmed functional failures.

## 7. Unrequested Functionality

The audit identified the following additional implementation elements:

| Element | Classification for subsequent evaluation |
|---|---|
| GET /api/health | Potential supporting feature |
| POST /api/mfa/verify | Supporting API |
| reset_lockout helper | Unspecified internal helper |
| Navbar verification badge | Additional interface feedback |
| Transfer toast notifications | Additional interface feedback |

Their final classification as beneficial support or unnecessary redundancy requires qualitative evaluation. Their presence alone does not establish a defect.

## 8. Human Intervention

The post-implementation audit was initiated through one additional explicit user prompt.

The audit reported findings without applying corrective changes.

- Human-requested source-code corrections during this audit: 0.
- Specification modifications during this audit: 0.
- Source-code modifications during this audit: 0.
- Confirmed compliance discrepancy: 1.
- Unresolved technical and testing concerns: documented above.

The two autonomous code corrections recorded during the initial implementation remain separate from human-directed post-implementation corrections.

## 9. Pending Experimental Evidence

The following measurements are not established by this audit:

- Gemini session input tokens.
- Cached input tokens.
- Output tokens.
- Estimated financial cost.
- Total session processing time.
- Authoritative session interaction and tool-call statistics.
- SonarQube bugs, vulnerabilities, code smells, technical debt, cognitive complexity, duplication, and ratings.
- Visual and interactive application evaluation.
- Actual executed requirement acceptance checks beyond the existing automated tests.

These must not be estimated or substituted with fabricated values.

## 10. Audit Conclusion

The read-only analysis reported 50 satisfied requirements and one partially satisfied requirement out of 51 identified obligations.

The implementation produced 2,529 production source lines against 235 specification lines, with 40 existing automated tests reported as passing.

The principal confirmed specification discrepancy concerns the incomplete HTTP 428 response body. Additional observations involve floating-point monetary representation, transaction rollback handling, incomplete boundary/concurrency testing, and functionality not explicitly prescribed by the specifications.

This record represents the initial post-implementation audit checkpoint. Later specification corrections, implementation changes, and final metrics belong to separate append-only experimental records.