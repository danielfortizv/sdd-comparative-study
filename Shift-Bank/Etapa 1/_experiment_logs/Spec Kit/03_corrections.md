# Spec Kit - Stage 1 Corrections

## Summary

- Initial requirement clarification rounds: 1
- Human specification correction rounds: 5
- Individual specification issues corrected: 13
- Post-implementation correction rounds: 0
- Manually edited application source files: 0

- Human planning-artifact correction rounds: 3
- Individual planning-artifact issues corrected/targeted: 6

## Planning Artifact Corrections

- Human planning-artifact correction rounds: 2
- Individual planning issues corrected: 5

## Correction Round 001

### Classification
- Type: Human governance/specification review
- Phase: Constitution
- Artifact: `.specify/memory/constitution.md`

### Issues Identified

1. The generated constitution introduced mandatory unit and integration tests.
2. The generated constitution introduced PR-specific review and compliance requirements.

### Result

- Both issues were corrected.
- Validation was made technique-neutral.
- PR-specific requirements were removed.
- Application code modified: No.

## Correction Round 002

### Classification
- Type: Human governance/specification review
- Phase: Constitution
- Artifact: `.specify/memory/constitution.md`

### Issue Identified

1. The Governance section still mandated regular compliance reviews using Spec Kit tools, which conflicts with the requirement that the experimental workflow remain tool-neutral.

### Human Intervention

Requested removal of the Spec Kit-specific review mechanism while preserving general compliance review requirements.

### Result

- Pending.
- Application code modified: No.

## Correction Round 002

### Classification
- Type: Human governance/specification review
- Phase: Constitution
- Artifact: `.specify/memory/constitution.md`

### Issue Identified

1. The Governance section still mandated regular compliance reviews using Spec Kit tools, which conflicted with the requirement that the experimental workflow remain tool-neutral.

### Human Intervention

Requested removal of the Spec Kit-specific review mechanism while preserving general compliance review requirements.

### Result

- Successfully corrected.
- Governance compliance review is now tool-neutral.
- Constitution version after correction: 1.2.0
- Application code modified: No.

## Correction Round 003

### Classification
- Type: Human feature specification review
- Phase: After initial clarification, before planning
- Artifact: `specs/001-shift-bank-stage1/spec.md`

### Issues Identified

1. Account overview introduced display of account identifiers/account numbers that were not required by the Stage 1 scope.
2. Transaction history expanded scope to deposits, withdrawals, salary deposits, and retail purchases.
3. Transaction entities introduced a resulting balance field that was not part of the approved baseline.
4. The specification did not explicitly reject transfers where source and destination are the same account.
5. MFA lifecycle behavior was incomplete: expiration, invalid-code retry behavior, balance revalidation, and terminal states were not fully specified.
6. Pre-seeded history was not aligned with the frozen experimental baseline.
7. Success criteria introduced arbitrary timing thresholds that were not part of the experimental baseline.

### Human Intervention

Requested revision of the generated feature specification to restore the frozen
Stage 1 experimental baseline and remove invented or expanded requirements.

### Result

- Successfully corrected.
- Individual specification issues corrected: 7.
- Requirements checklist: PASS.
- Application code modified: No.

## Correction Round 004

### Classification
- Type: Human feature specification review
- Phase: After Clarify, before Plan
- Artifact: `specs/001-shift-bank-stage1/spec.md`

### Issue Identified

1. The specification still assumed in-memory or non-persistent application state,
   which conflicted with the frozen experimental baseline requiring persistent
   server-side state.

### Human Intervention

Requested removal of the non-persistent assumption and required persistent
server-side storage for accounts, balances, transaction histories, transfer
records, transfer states, and pending MFA transfers.

### Result

- Successfully corrected.
- Persistent server-side state is now explicitly required.
- Concrete storage technology remains deferred to implementation planning.
- Requirements checklist: PASS.
- Application code modified: No.

## Correction Round 005

### Classification
- Type: Human feature specification review
- Phase: After Plan, before task generation
- Artifact: `specs/001-shift-bank-stage1/spec.md`

### Issues Identified

1. Closing or cancelling the MFA modal had ambiguous persisted-state behavior.
2. MFA expiration semantics implied a background transition despite no scheduler
   being required for Stage 1.

### Human Intervention

Requested explicit lifecycle semantics:
- Closing/cancelling the MFA modal leaves the transfer persisted as PENDING_MFA.
- No CANCELED state is introduced.
- No balance changes occur on cancellation.
- Expiration is evaluated on demand when confirmation is attempted after
  the five-minute deadline.
- No background scheduler, worker, daemon, or active timer process is required.

### Result

- Successfully corrected.
- Existing four-state lifecycle preserved:
  PENDING_MFA, COMPLETED, FAILED, EXPIRED.
- Requirements checklist: PASS.
- Application code modified: No.


---

## Planning Artifact Corrections

### Planning Correction Round 001

#### Classification
- Type: Human planning artifact review
- Phase: After initial Plan, before task generation
- Artifacts: `plan.md`, `research.md`, `data-model.md`, `contracts/api.md`, `quickstart.md`

#### Issues Identified

1. The persistence design required an `expires_at` value for all transfers, including standard and pre-seeded `COMPLETED` transfers, even though MFA expiration only applies to transfers entering `PENDING_MFA`.

2. Database-level atomicity was not explicitly defined for successful transfer execution, leaving open the possibility of partial balance or state updates.

3. The development-time communication strategy between the Vite frontend and FastAPI backend was not explicitly defined.

#### Human Intervention

Requested:
- `expires_at` must be nullable and only populated when MFA applies.
- Standard and pre-seeded completed transfers must not receive artificial MFA expiration timestamps.
- Source debit, destination credit, and transfer-state update must execute atomically within a single SQLite transaction.
- A minimal local frontend/backend communication strategy must be explicitly documented without introducing external infrastructure.

#### Result

- Successfully corrected.
- `expires_at` is nullable and only used for `PENDING_MFA` transfers.
- Transfer execution is explicitly defined as an atomic SQLite transaction.
- Local Vite/FastAPI communication is explicitly documented.
- Individual planning issues corrected: 3.
- Application code modified: No.

---

### Planning Correction Round 002

#### Classification
- Type: Human planning artifact review
- Phase: Final Plan review, before task generation
- Artifacts: `plan.md`, `research.md`, `data-model.md`, `contracts/api.md`, `quickstart.md`

#### Issues Identified

1. The atomic transfer design performed monetary arithmetic inside SQLite using `REAL` casts, conflicting with the fixed technical baseline requiring all monetary calculations to use Python `Decimal`.

2. The development-time frontend/backend communication strategy remained ambiguous because both FastAPI CORS middleware and a Vite development proxy were presented as alternatives.

#### Human Intervention

Requested:
- Monetary arithmetic must occur exclusively in Python using `decimal.Decimal`.
- Persisted decimal strings must be read from SQLite, converted to `Decimal`, calculated in Python, converted back to canonical decimal strings, and written using parameterized SQL statements.
- Source debit, destination credit, and transfer-state update must remain within the same atomic SQLite transaction.
- FastAPI `CORSMiddleware` allowing `http://localhost:5173` must be the single development-time communication strategy.
- The Vite proxy alternative must be removed.
- No external proxy, gateway, or additional infrastructure may be introduced.

#### Result

- Successfully corrected.
- All monetary arithmetic is now performed exclusively in Python using `decimal.Decimal`.
- SQLite receives pre-calculated decimal strings through parameterized statements.
- SQLite `REAL` casts and SQL monetary arithmetic were removed.
- FastAPI `CORSMiddleware` with `http://localhost:5173` is now the single development-time communication strategy.
- The Vite proxy alternative was removed.
- Individual planning issues corrected: 2.
- Application code modified: No.

### Planning Correction Round 003

#### Classification
- Type: Human planning artifact review
- Phase: Final Plan review, before task generation
- Artifact: `data-model.md`

#### Issue Identified

1. The atomicity design instructed the transaction to ROLLBACK when source-balance
   re-validation fails during MFA confirmation. This conflicts with the approved
   lifecycle requirement that an insufficient source balance at confirmation
   must persist the transfer state as FAILED.

#### Human Intervention

Requested:
- If balance re-validation succeeds, source debit, destination credit, and the
  COMPLETED transition must be committed atomically.
- If balance re-validation fails during valid MFA confirmation, account balances
  must remain unchanged, but the transfer state must be updated to FAILED and
  committed.
- ROLLBACK must be reserved for unexpected database or technical failures.

#### Result

- Successfully corrected.
- Insufficient funds during valid MFA confirmation now persist the transfer as FAILED.
- Account balances remain unchanged in that business-failure path.
- The FAILED state transition is committed.
- ROLLBACK is reserved for unexpected database or technical failures.
- Individual planning issues corrected: 1.
- Application code modified: No.