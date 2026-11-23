# Stage 4 Implementation Authorization and Scope

## Gate B approval

On 2026-11-16 the researcher explicitly approved Gate B and accepted the Stage 4 specification, technical plan, API/event contracts, data model, and 68 implementation tasks. The researcher also accepted the 24 contract-review checklist items based on the documented 24/24 PASS assessment in E4-SK-04, while explicitly stating that this was acceptance of an agent audit and not independent human verification.

The exact authorization is recorded in `../_experiment_logs/Spec Kit/decisiones/E4_SPECKIT_GATE_B_APPROVAL_2026-11-16.md`. The E4-SK-04 audit limitations remain applicable.

## Approved compatibility contract

Preserve inherited COP accounts, exact balances and history; never reinterpret COP as USD. Add the four D-02 accounts only if absent and fail on incompatible identity/value conflicts. Keep account currency fixed. Use exact Decimal/rational arithmetic for USD/EUR/GBP, no COP conversion, same-currency internal transfers, COP legacy limits/MFA, and the approved USD-equivalent controls. Preserve separate append-only domain events and HMAC audit, atomic projections, replay, UUID idempotency and optimistic versions.

## This implementation milestone

Authorized work is limited to the financial persistence foundation, COP-preserving and idempotent migration, additive account provisioning, exact money, same-currency transfers, USD/EUR/GBP conversion, their idempotency/version/limit/MFA controls, and focused automated verification using disposable databases. No Stage 3 path, historical database, secret, Docker volume, Tessl artifact, production deployment, load benchmark, or unrelated SDD tool is in scope. ACH/recurring, frontend, deployment and broader acceptance remain future tasks unless required for safe compatibility.

No Gate B authorization extends beyond this scoped implementation milestone.
