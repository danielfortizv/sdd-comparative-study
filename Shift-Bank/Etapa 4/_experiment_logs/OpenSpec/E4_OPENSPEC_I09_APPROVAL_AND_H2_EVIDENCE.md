# Iteration 09 — Researcher approval, TLS containment, and H2 evidence

## Approval record

The researcher explicitly approved all four decisions in a message received for Iteration 09.

### Decision 1 — TLS security: APPROVED

“I authorize moving only the E4 dev-cert.pem and dev-key.pem files to C:\Users\danie\AppData\Local\ShiftBank-E4\secrets\tls\. Use restricted ACLs, preserve E3 and all historical evidence, and do not overwrite, disclose, regenerate, or rotate credentials.”

### Decision 2 — D-02 migration: APPROVED

The researcher approved legacy currency COP; one-time simulated conversion of 4,000 COP = 1 USD; retaining internal IDs acc_checking and acc_savings; public references CHK-1001 and SAV-2001 with legacy compatibility; initial converted USD 1,250.00 and USD 3,750.00 for the reported state; EUR-3001 and GBP-4001 at zero; explicit deviation from reference balances; preservation of transaction identity, timestamps, monetary provenance, and audit integrity; a deterministic snapshot boundary without double-posting; exact arithmetic and verifiable reconciliation; no artificial balancing entries; and fail-closed behavior when invariants cannot be proven.

### Decision 3 — Legacy states: APPROVED

The researcher approved a pre-migration check requiring no pending ACH, no pending MFA authorization, no active or paused recurring schedule requiring migration, and zero current-day transfer-limit usage. Failure aborts without financial changes. Pending obligations must not be auto-resolved, cancelled, settled, or converted; terminal historical records remain preserved. The limitation that this does not prove every populated database migratable is explicit.

### Decision 4 — H2 authoring: AUTHORIZED

The researcher explicitly authorized a native OpenSpec Stage 4 proposal, design, specification deltas, acceptance scenarios, implementation tasks, and strict validation under D-01 through D-14 and the approved D-02 deviation. Application code/tests, financial migration execution, deployment, load tests, Stage 3 changes, commits, and archival remain prohibited. Implementation requires separate approval after review.

## TLS containment

The only move operation targeted E4 deployment/certs/dev-cert.pem and deployment/certs/dev-key.pem. Both source files were regular, non-reparse files (1,070 and 1,704 bytes); the approved external destination had no pre-existing target directory or file collision, and checked destination ancestors were not reparse points. E3 copies were recorded before the operation and remained present afterward at the same respective sizes. No certificate or private-key contents were read, displayed, copied to evidence, or hashed.

The move completed to C:\Users\danie\AppData\Local\ShiftBank-E4\secrets\tls\. E4 source paths are absent; external destination files are present. The first post-move ACL check found inherited source ACEs on the files, so verification did not pass at that point. The already-moved destination files were then assigned protected file ACLs and rechecked. Final result: directory ACL inheritance disabled; each file ACL inheritance disabled; each contains exactly three explicit Full Control ACEs for the current user, SYSTEM, and Builtin Administrators. Destination and file paths were checked as non-reparse objects. No retry, overwrite, duplicate temporary copy, key generation, rotation, Compose modification, or deployment occurred. The E3 paths were never targets of a write operation.

The original H0 inventory and manifests were not rewritten. The previously sanitized manifest remains the nonsensitive baseline. Compose was not changed or run; deployment readiness after relocating certificate and environment material is NOT VERIFIED and will need approved configuration-path handling before deployment.

## Native OpenSpec artifacts

Installed native CLI: OpenSpec 1.9.0, schema spec-driven; Node.js v24.19.0; npm 11.17.0. PowerShell blocked the openspec.ps1 shim under the machine execution policy; the installed CLI JavaScript entry point was invoked directly with Node. No package installation was performed.

Change: openspec/changes/stage4-multicurrency-event-sourcing-cqrs/

Native artifacts: proposal.md, design.md, tasks.md, 15 specification delta files, plus CLI-generated README.md and .openspec.yaml. The native status command reported 4/4 artifacts complete. The specification set contains 26 requirements and 73 acceptance scenarios.

Strict validation commands and observed output:

- node C:\nvm4w\nodejs\node_modules\@fission-ai\openspec\bin\openspec.js validate stage4-multicurrency-event-sourcing-cqrs --strict
- Exit code: 0
- Output: Change 'stage4-multicurrency-event-sourcing-cqrs' is valid

- node C:\nvm4w\nodejs\node_modules\@fission-ai\openspec\bin\openspec.js validate --all --strict
- Exit code: 0
- Output: validation listed spec/bank-accounts, spec/mfa, change/stage2-banking-enhancements, change/stage3-banking-security-load-deployment, change/stage4-multicurrency-event-sourcing-cqrs, spec/transaction-history, and spec/transfers; Totals: 7 passed, 0 failed (7 items).

An initial strict validation correctly rejected four MODIFIED requirements because inherited scenario names were omitted. Those scenario names were restored with approved Stage 4 behavior; both final strict validations above then passed. No application tests or builds were run because application code/tests were not changed.

### SHA-256 artifact inventory

Hashes below are for the final Stage 4 change artifacts at H2 validation. Paths are relative to Etapa 4/OpenSpec.

| Path | Bytes | SHA-256 |
|---|---:|---|
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/.openspec.yaml | 164 | 717136fca51b130250ce1ec7702fe7f009cba05b2fa5c35feb08158366912cef |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/README.md | 150 | 247791bd049b116b90e47df9d345bc3f72a93f5e32f5e34c24d050e4058e9c5c |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/proposal.md | 3733 | b125445719a9509b77375e3347d4caa3135a5d68aecedb488ba1a2126c99595f |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/design.md | 9299 | 750feb89acd5ddfa27cfe2925dd3c7316343079bf3f33ed62f42e8b158bb00d9 |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/tasks.md | 5270 | 85f4201c73d0fa5073b3f3b124867b9d84764f17c053d8e8e3866c34808c173d |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/specs/ach-operations/spec.md | 1384 | 271fdb530cbc1084a0e9c569c83d25e13905a2887310d285ab4a597615874fb8 |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/specs/bank-accounts/spec.md | 1819 | 2d1812a272a32b0ba00f47d7434a77117b527d05abf68a82c3fa8ce58171b719 |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/specs/client-and-api-compatibility/spec.md | 2378 | 30916e82a4bbc794d5ea2c0ed79d56f13f9802e33a0502068fb1b921b408b681 |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/specs/cqrs-projections/spec.md | 1899 | 3c71d75834b5af01cf2bb60b26fa9683d866f8a2df89bb43165cb9b0b5278b75 |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/specs/currency-conversion/spec.md | 2888 | 163104c113a83f08485dd0b17cfd8b98e2b359b0c44f5419f8cc3a5db62343c3 |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/specs/deployment-continuity/spec.md | 1541 | 90b219462a8f8d8cecf36bd56321d8d12838604b7a9bcda29e35a84a6eb96efd |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/specs/domain-events/spec.md | 2692 | c33b93852245d30e38fe3486ba206f935e02d877199a6a0b4ab424fff0c9d329 |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/specs/financial-commands/spec.md | 2227 | 8ee82db7166b2a1085abda397124ae030b38115b1fa092f7d471748820f4ce4d |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/specs/financial-integrity/spec.md | 2099 | 5fc16990eb268e91d408acc67df4c756a8313e6b8221d24aa05ead4fc0ca08a6 |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/specs/mfa/spec.md | 1420 | df99398cd01225cc8b5ba75613a963e642a6a0ed3932e920ba4fa06b346722f6 |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/specs/migration-and-reconciliation/spec.md | 6891 | 1a8d535ccfcc4f3c732b4469a58dcffaeab0679d97071d978cbd5f32d50895be |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/specs/recurring-operations/spec.md | 2399 | 76136b6f57a29efca5115961a29807201a4cea2237e047cec01fe2f900456ecd |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/specs/transaction-history/spec.md | 1469 | 6715f353c9d8b3103af659b6dadc12ebc4923570a3e1ef2ef6cd18e3fbd7a344 |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/specs/transfer-limits/spec.md | 1619 | 220e3e3bdb2fa2be58e31fcc96ce98bea1ca7c5437f773b39a0191115dce73e9 |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/specs/transfers/spec.md | 1349 | 09dae6aa94c65cb6110103d1bd5cb820cc8c32d165cf2ce64b4d6870a07ad74e |

## Evidence limitations and status

The change is specification-only and is awaiting researcher review. No financial migration, application code/test change, baseline rerun, deployment, load test, commit, or archive occurred. H0 outcomes remain inherited from earlier evidence and were not repeated. The final focused Git status reports the new native change artifacts only under the OpenSpec change path; a repository-wide status also showed unrelated Kiro and Stage 3 Spec Kit paths, which were not modified or attributed to this iteration.

Session ID, authoritative tool-call count, effective model identity, wall-clock duration, agent processing duration, input/output/cache tokens, and cost: N/D. Two researcher messages were observed in this iteration (authorization request and explicit approval response). No quantitative effort metric is inferred.
