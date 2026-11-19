# Iteration 10 — H2 approval evidence

## Authorization

The researcher explicitly approved Alternative A: convert persisted per-user COP transfer limits at the approved one-time rate of 4,000 COP/USD; round once with ROUND_HALF_UP; cap at the D-07 ceilings; require a positive minimum of USD 0.01 or fail closed; record rounding and cap adjustments; perform the migration atomically and idempotently; and prevent rollback from overwriting subsequent limit changes.

This approval authorizes specification updates only. It does not authorize implementation, migration execution, deployment, source/test changes, or archival.

## Specification updates

Updated only these native Stage 4 artifacts:

- `design.md`: records the approved limit conversion design and removes the now-resolved limit policy question.
- `tasks.md`: replaces the pending decision task with implementation and acceptance verification tasks.
- `specs/transfer-limits/spec.md`: adds the deterministic per-user conversion requirement and scenarios for inherited defaults, custom settings, minimum, ceilings, repeat migration, changed source, and rollback protection.
- `specs/migration-and-reconciliation/spec.md`: includes converted limits in atomic migration/recovery and covers preservation of subsequent limit edits during rollback.

No application code, tests, financial data, Stage 3 content, credentials, Compose/deployment configuration, or prior evidence was changed. Baseline tests and builds were not rerun.

## Contract details

For each persisted user-specific setting, compute COP / 4000 exactly, round once to cents using ROUND_HALF_UP, then cap per-transfer at USD 5,000.00 and daily at USD 10,000.00. Record source COP, exact quotient, rounded amount, effective amount, rounding residual, and cap adjustment. Reject results below USD 0.01 without rounding upward. The inherited defaults map to USD 1,250.00 per transfer and USD 2,500.00 daily. A repeated identical source snapshot is a no-op; changed, missing, malformed, or unreconcilable settings fail closed. Rollback cannot overwrite post-cutover limit changes.

At specification freeze the change contains 15 delta specifications, 28 requirements, and 83 scenarios. The preceding I09 evidence recorded 27 requirements and 76 scenarios before this approved addition.

## Native validation

OpenSpec CLI version: 1.9.0. Strict syntax was confirmed with the installed CLI help.

Command:
`node C:\nvm4w\nodejs\node_modules\@fission-ai\openspec\bin\openspec.js validate stage4-multicurrency-event-sourcing-cqrs --strict --no-interactive`

Exit code: 0. Output: `Change 'stage4-multicurrency-event-sourcing-cqrs' is valid`.

Command:
`node C:\nvm4w\nodejs\node_modules\@fission-ai\openspec\bin\openspec.js validate --all --strict --no-interactive`

Exit code: 0. Output: 7 passed, 0 failed (7 items), including the Stage 4 change.

The inherited I09 baseline recorded 7/7 strict validation; it was not rerun as a separate baseline. No application regression suite, build, migration, or deployment was run in this iteration.

## Changed artifact hashes

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `design.md` | 10151 | `f48275207b68338bc45f02bf7b3be1438ff1bc4f5c009d83d26bfac11d00ff19` |
| `tasks.md` | 5651 | `c6b3e5ea878eb95b2730df9a9c20595711392ae404a467008c51e73cf44cf452` |
| `specs/transfer-limits/spec.md` | 5350 | `db4a87d4d84b2bb8b14de40fc6aed38c815203b3f0f1ff85ea6c79e7e45d0bb5` |
| `specs/migration-and-reconciliation/spec.md` | 7263 | `62db29e4dc1fc51ae6152b9dc33f6b1b6af5bd5c13e386fde727ff2085842393` |

The complete 20-file change artifact inventory, sizes, and SHA-256 values are in `E4_OPENSPEC_I10_FINAL_ARTIFACT_HASHES.json`. The manifest describes the final post-validation specification state.

## H2 handoff

H2 specification authoring and strict validation are complete for researcher review. H3 implementation remains unauthorized and has not started. No Git commit or OpenSpec archival was performed.
