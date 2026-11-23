# Iteration 09 — H2 finalization addendum

This addendum supplements E4_OPENSPEC_I09_APPROVAL_AND_H2_EVIDENCE.md and E4_OPENSPEC_I09_H2_TRACEABILITY.md. It preserves those first-pass evidence files and records the final review refinements and hashes; it does not alter the approved business contracts.

## Final refinement

The final review made inherited configurable limits explicit: users retain configurable effective limits within the D-07 USD 5,000.00 per-operation and USD 10,000.00 daily ceilings. Deployment requirements now explicitly retain exactly one scheduler owner for each shared SQLite database.

One material migration detail remains unapproved: treatment of persisted configurable per-transfer and daily limit values stored as untyped legacy COP amounts. The researcher approved D-07 ceilings and the COP/USD account migration policy, but did not say whether saved legacy limit settings are converted, reset to the D-07 ceilings, or carried as lower USD-equivalent thresholds. No choice is encoded. The design lists the question, the tasks require researcher resolution before implementing limit or migration changes, and implementation/migration remains unauthorized.

## Final artifact replacements and counts

The following final hashes supersede the hashes for these four files in the first-pass H2 evidence. All other artifact hashes in that evidence remain unchanged.

| Path relative to Etapa 4/OpenSpec | Bytes | SHA-256 |
|---|---:|---|
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/design.md | 9911 | 95297070e7b9a590d76442fb6010b64b265fde07caeea8f3481281bd14b99239 |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/tasks.md | 5440 | 79fba739262cadaeb91a1a1049775091695cd9ff9ef8cd465f10fa2be20dd3bd |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/specs/deployment-continuity/spec.md | 1882 | c63e5cbb9c409297d89c72893c60eb1ec9b8bb6f84aeee4b6452d41f2036090b |
| openspec/changes/stage4-multicurrency-event-sourcing-cqrs/specs/transfer-limits/spec.md | 2593 | 3bc4c3c1bfa3a17d6a9ea4bd9aa31515fb459f2fdbdcfeaceb3d2dc439fe908e |

Final change totals: 15 spec delta files, 27 requirements, 76 explicit scenarios; OpenSpec status 4/4 artifacts complete.

## Final strict validation

Command: node C:\nvm4w\nodejs\node_modules\@fission-ai\openspec\bin\openspec.js validate stage4-multicurrency-event-sourcing-cqrs --strict
Exit code: 0
Output: Change 'stage4-multicurrency-event-sourcing-cqrs' is valid

Command: node C:\nvm4w\nodejs\node_modules\@fission-ai\openspec\bin\openspec.js validate --all --strict
Exit code: 0
Output: Totals: 7 passed, 0 failed (7 items); the seven items were four inherited specs, the two completed inherited changes, and the Stage 4 change.

No application tests, builds, migration, deployment, commit, or archive operation was run. No application code, tests, financial data, Stage 3 content, or other SDD workspace was changed.
