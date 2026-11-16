# Stage 4 Contract Requirements Review

**Purpose**: Reviewer-owned checklist for completeness, clarity, consistency, and traceability of the Stage 4 contract  
**Created**: 2026-11-16  
**Feature**: [spec.md](../spec.md)

**Ownership**: The researcher/reviewer owns these items. `[x]` records the researcher's E4-SK-05 acceptance of the E4-SK-04 agent review; it does not mean independent human verification of implementation or testing.

## Requirement Completeness

- [x] CHK001 Are retained COP accounts, exact balances, currencies, and legacy histories distinguished from the four added reference accounts? [Completeness, Spec §Purpose and Scope; §FR-002–FR-005]
- [x] CHK002 Are all provisioning conflict and repeat-run outcomes specified without resetting financial values? [Completeness, Spec §FR-003; AC-02–AC-03]
- [x] CHK003 Are opening snapshot and legacy transaction import semantics explicit enough to prevent double counting? [Completeness, Spec §FR-005; AC-19]
- [x] CHK004 Are COP display and estimated USD-total exclusions stated consistently? [Consistency, Spec §FR-004; AC-04, AC-34]

## Requirement Clarity

- [x] CHK005 Are exact FX directions, rational rates, and final rounding rules explicit for every supported pair? [Clarity, Spec §FR-010–FR-012; AC-11–AC-12, AC-31–AC-32]
- [x] CHK006 Are COP and USD-equivalent limit/MFA boundaries independently stated, including equality behavior? [Clarity, Spec §FR-014–FR-015; AC-07–AC-09, AC-27, AC-40]
- [x] CHK007 Are supported ACH and recurring currencies unambiguous, including the COP exception? [Clarity, Spec §FR-016–FR-018; AC-15–AC-18]
- [x] CHK008 Are idempotency and version conflict requirements clear for every affected account and request replay? [Clarity, Spec §FR-019–FR-020; AC-28–AC-30, AC-41]

## Requirement Consistency

- [x] CHK009 Do requirement, API, event, and task artifacts use one consistent definition of a domain event versus an audit record? [Consistency, Spec §FR-006–FR-009, FR-021–FR-022]
- [x] CHK010 Do event version increments and composite operation semantics agree across transfers, conversions, and ACH lifecycle changes? [Consistency, Spec §FR-007–FR-009, FR-017, FR-020]
- [x] CHK011 Are the documented COP deviations limited to D-01, D-02, D-07, D-08, and D-10 effects accepted in the delegated contract? [Consistency, Spec §Contract Provenance; §D-01–D-14 Traceability]

## Acceptance Criteria Quality

- [x] CHK012 Can each REQ-01–REQ-06 be traced to named FRs and unique AC IDs? [Traceability, Spec §Acceptance Traceability]
- [x] CHK013 Can each D-01–D-14 decision be traced to at least one observable acceptance criterion and a planned verification task? [Traceability, Spec §D-01–D-14 Traceability]
- [x] CHK014 Do criteria avoid presenting historical E1–E3 measurements as E4 results? [Clarity, Spec §FR-026–FR-027; AC-42]

## Scenario and Edge Case Coverage

- [x] CHK015 Are migration rollback, repeated migration, corrupt data, and snapshot/history disagreement requirements covered? [Coverage, Spec §Edge Cases; FR-024]
- [x] CHK016 Are duplicate events, replay order, projection mismatch, and concurrent-version conflicts covered? [Coverage, Spec §Edge Cases; AC-20–AC-21, AC-37, AC-41]
- [x] CHK017 Are ACH settlement and repeated refund failure paths defined without double debit or credit? [Coverage, Spec §FR-017; AC-15–AC-16]
- [x] CHK018 Are missing/invalid encryption keys and audit-chain failures covered without plaintext fallback? [Coverage, Spec §FR-021–FR-022; AC-39]

## Non-Functional Requirements and Dependencies

- [x] CHK019 Are exact arithmetic and no-fee/no-float requirements explicit at both backend and frontend boundaries? [Completeness, Spec §FR-010–FR-011; AC-23]
- [x] CHK020 Are external FX/banking services explicitly excluded and the fixed rate source identified? [Dependency, Spec §Assumptions and Out of Scope]
- [x] CHK021 Is the preserved FastAPI/React/SQLite/Compose/Nginx/TLS capability separated from a claim that deployment was tested? [Clarity, Spec §FR-023, FR-027; AC-24]

## Provenance and Deviations

- [x] CHK022 Does the record distinguish the delegated prospective approval from missing historical approvals and original seed provenance? [Provenance, Spec §Contract Provenance]
- [x] CHK023 Are inherited account IDs, limits, MFA threshold semantics, and COP ACH compatibility represented as explicit deviations rather than defects? [Deviation, Spec §D-01–D-14 Traceability]
- [x] CHK024 Are migration, rollback, and E4 verification tasks clearly future work requiring Gate B? [Scope, Spec §Assumptions and Out of Scope]

## Notes

- Researcher acceptance was recorded in `E4_SPECKIT_GATE_B_APPROVAL_2026-11-16.md`, based on the 24/24 PASS agent audit in `E4_SPECKIT_FINAL_CONTRACT_AUDIT.md`. This is not independent human verification of implementation or test results.
- The researcher authorized implementation under Gate B on 2026-11-16; checklist acceptance is requirements review only and does not assert functional tests have passed.
- This checklist is not a functional test plan and does not authorize implementation.
