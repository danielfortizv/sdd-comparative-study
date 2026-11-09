# Tessl — Stage 1 — Specification Correction Record 01

## Correction Identification

- Case study: Shift Bank.
- Stage: 1.
- Tool: Tessl.
- Correction cycle: 01.
- Date: November 1, 2026.
- Trigger: Findings from the first post-implementation audit.
- Intervention type: Human-requested specification clarification.
- Status: Specification changes approved; implementation pending.

## 1. Identified Issues

**Issue 1 — TRF-06: HTTP 428 response contract**

The initial implementation returned `{"detail": "MFA_REQUIRED"}` instead of the complete response required by the specification.

The specification already described the expected response, but its Data Contract section lacked an explicit schema for the error.

**Issue 2 — MFA threshold boundary verification**

The initial tests did not explicitly verify the transition between non-sensitive and sensitive transfers at USD 1,000.00 and USD 1,000.01.

This was a testing gap rather than a confirmed failure in the existing threshold implementation.

## 2. Specification Modifications

The agent activated Tessl's `spec-writer` skill and modified two existing specification files.

### `specs/transfers.spec.md`

- Added `MfaRequiredResponse` to the Data Contract.
- Defined the required `detail` and `message` fields.
- Explicitly established that USD 1,000.00 does not require MFA.
- Explicitly established that USD 1,000.01 requires MFA.

Recorded edit operation: +6 lines, -2 lines; net change of +4 lines.

### `specs/mfa.spec.md`

- Clarified that transfers of exactly USD 1,000.00 bypass MFA.
- Clarified that transfers of USD 1,000.01 require a valid Security PIN.
- Added references to transfer tests for both boundary conditions.

Recorded edit operation: +4 lines, -2 lines; net change of +2 lines.

### Modification Summary

- Specification files modified: 2.
- Specification edit operations: 2.
- Net specification line change: +6.
- Initial measured specification LOC: 235.
- Expected specification LOC after edits: 241, pending filesystem recount.
- New functional capabilities requested: 0.
- Previously approved functional scope preserved.

## 3. Human Feedback

One explicit corrective prompt initiated this specification clarification cycle.

The agent requested approval for the modified specifications through an interactive confirmation. The user approved both specification changes.

Human-requested correction iterations in this cycle: 1.

Interactive specification approval responses in this cycle: 1.

## 4. Implementation Boundary

During this correction phase:

- Application source code was not modified.
- Automated tests were not modified.
- Dependencies and project configuration were not modified.
- Two specification files were modified.
- Implementation of the correction was intentionally deferred until after human approval.

## 5. Pending Verification

The approved specifications establish the following acceptance conditions:

1. HTTP 428 returns both required JSON fields.
2. USD 1,000.00 transfers execute without MFA.
3. USD 1,000.01 transfers require MFA.
4. Existing functionality remains operational.
5. Regression tests verify the corrected behavior.

The results of implementation and subsequent testing are not part of this record and must be documented separately.

## 6. Experimental Interpretation

This cycle represents a human-directed correction of an incomplete implementation contract and a specification clarification addressing insufficient boundary-test coverage.

The correction contributes to the measurement of specification edits, human feedback, correction iterations, tool interactions, and subsequent code changes.

It must be distinguished from the two autonomous code corrections performed by Gemini during initial implementation.