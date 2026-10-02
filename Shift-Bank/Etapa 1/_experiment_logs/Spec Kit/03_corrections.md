# Spec Kit - Stage 1 Corrections

## Summary

- Initial requirement clarification rounds: 1
- Human specification correction rounds: 5
- Individual specification issues corrected: 13
- Human planning-artifact correction rounds: 3
- Individual planning-artifact issues corrected/targeted: 6
- Human task-artifact correction rounds: 1
- Individual task issues targeted: 5
- Post-implementation compliance review: 1 — no correction required
- Final validation correction: 1 — T036 reverted to pending
- Manually edited application source files during human correction rounds: 0

## Specification Corrections

### Correction Round 001 — Constitution

Issues:
1. Generated constitution introduced mandatory unit/integration tests.
2. Generated constitution introduced PR-specific review/compliance requirements.

Result:
- Corrected.
- Validation made technique-neutral.
- PR-specific requirements removed.
- Application code modified: No.

### Correction Round 002 — Constitution

Issue:
- Governance still required compliance reviews using Spec Kit tools.

Intervention:
- Remove the Spec Kit-specific review mechanism while preserving general compliance review.

Result:
- Corrected.
- Governance compliance review became tool-neutral.
- Constitution version: 1.2.0.
- Application code modified: No.

### Correction Round 003 — Feature Specification

Issues:
1. Unnecessary account identifiers in the UI.
2. Transaction-history scope expanded beyond transfers.
3. Resulting balance field added without approval.
4. Same-account transfers were not explicitly rejected.
5. MFA lifecycle was incomplete.
6. Seeded history did not match the frozen baseline.
7. Arbitrary timing targets were introduced.

Result:
- Corrected.
- 7 individual issues targeted.
- Requirements checklist passed.
- Application code modified: No.

### Correction Round 004 — Feature Specification

Issue:
- Specification assumed non-persistent/in-memory state.

Result:
- Persistent server-side state explicitly required.
- Storage technology remained deferred to planning.
- Application code modified: No.

### Correction Round 005 — Feature Specification

Issues:
1. MFA modal close/cancel behavior was ambiguous.
2. Expiration semantics implied a background transition.

Result:
- Corrected.
- Closing/canceling leaves the transfer `PENDING_MFA`.
- No `CANCELED` state.
- No balance changes on cancellation.
- Expiration evaluated on confirmation after five minutes.
- No scheduler, worker, daemon, or active timer process required.
- Application code modified: No.

## Planning Artifact Corrections

### Planning Correction Round 001

Issues:
1. `expires_at` was incorrectly required for every transfer.
2. Atomicity was not explicit.
3. Local frontend/backend communication was ambiguous.

Result:
- `expires_at` nullable and only used for `PENDING_MFA`.
- Successful transfer execution defined as an atomic SQLite transaction.
- Local Vite/FastAPI communication documented without external infrastructure.

### Planning Correction Round 002

Issues:
1. Monetary arithmetic was described using SQLite `REAL` casts.
2. CORS and Vite proxy were both presented as alternatives.

Result:
- Monetary arithmetic moved exclusively to Python `decimal.Decimal`.
- SQLite stores canonical decimal strings through parameterized SQL.
- FastAPI `CORSMiddleware` became the single local communication strategy.
- Vite proxy alternative removed.

### Planning Correction Round 003

Issue:
- Insufficient funds during MFA confirmation was incorrectly associated with ROLLBACK, conflicting with the required persistent `FAILED` state.

Result:
- Successful confirmation commits balances and `COMPLETED` atomically.
- Insufficient funds at confirmation leave balances unchanged but commit `FAILED`.
- ROLLBACK reserved for unexpected technical/database failures.

## Task Correction Round 001

Issues:
1. Seed semantics were ambiguous.
2. SQLite versus in-memory wording was inconsistent.
3. T033 introduced unsupported backend-log requirements.
4. T034/T035 imposed unsupported 100% coverage requirements.
5. Generated tasks needed a traceability/scope review.

Result:
- T004 explicitly separates initial balances from historical transaction logs.
- SQLite persistence consistently enforced.
- T033 limited to user-facing ID exposure.
- T034/T035 require implemented tests to pass without imposing artificial coverage.
- No new functionality, technologies, architecture, or scope introduced.
- Application code modified: No.

## Post-Implementation Compliance Review — Human Correction Round 002

Phase: Phase 6 implementation review.

Scope:
- HTTP status codes for MFA.
- Pending Sensitive Transfers widget.
- MFA state transitions.
- Five-minute expiration.
- Insufficient funds at initiation and confirmation.
- Transactional atomicity.
- Internal ID exposure.
- Test traceability.
- Technical scope.

Result:
- **NO CORRECTION REQUIRED**.
- The implementation was allowed to remain unchanged.
- No application source files were modified by the review.

## Final Validation Correction — T036

Issue:
- Previous automated report claimed T036 was manually completed without evidence of an actual human browser walkthrough.

Intervention:
- T036 reverted from `[X]` to `[ ]`.
- Application source code was not modified.
- Approved specification, plan, contracts, data model, and quickstart were not modified.

Current status:
- Scenario 1 manually passed.
- Scenarios 2–4 still require human execution.

## Implementation Correction Round 003 — Manual MFA validation findings

Observed during human browser validation after the initial Phase 7 report:

1. Expired MFA confirmation did not provide a user-visible explanation of the expiration result.
2. The frontend displayed `[object Object]` for structured backend errors.
3. Resuming a pending MFA transfer restarted the countdown at five minutes instead of restoring the remaining time.
4. The expired-confirmation scenario could not be exercised because the frontend disabled the Confirm action at zero seconds.

Intervention:
- First checked the approved Spec Kit artifacts before changing application code.
- Classified the findings as **IMPLEMENTATION ISSUES**, because the expected behavior was already defined by FR-012, API contract Section 4.3, and quickstart Scenario 6.
- Backend MFA errors were aligned with the approved structured response payloads for 401, 409, and 410 responses.
- Frontend error handling was made robust to structured error payloads so user-facing messages no longer render as `[object Object]`.
- MFA resume timing was changed to derive the remaining time from the persisted `expires_at` timestamp instead of resetting to 300 seconds.
- The Confirm action remains usable at expiration so the confirmation request reaches the backend and the on-demand `EXPIRED` transition can occur as specified.

Result:
- Targeted source-code correction completed.
- No specification, plan, data-model, contract, quickstart, or constitution change was required.
- Backend tests: 12/12 passed after correction.
- Frontend tests: 5/5 passed after correction.
- Production build: passed.
- T036 remains pending until the canonical quickstart scenarios are manually executed and evidenced.

## Final static-analysis validation

After implementation validation and correction, SonarQube was executed against the final Spec Kit implementation.

- Project: `shift-bank-stage1-speckit`
- Quality Gate: **Passed**
- Security: A — 0 open issues
- Reliability: C — 6 open issues
- Maintainability: A — 27 open issues
- Coverage: 0.0%
- Duplications: 2.1%
- Security Hotspots: 0

These results are recorded as validation evidence and were not treated as automatic requirements for further implementation correction.