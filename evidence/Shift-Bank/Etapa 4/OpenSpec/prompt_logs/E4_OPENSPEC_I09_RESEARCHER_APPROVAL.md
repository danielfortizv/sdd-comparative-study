# Iteration 09 — Exact researcher approval

The following is the researcher’s explicit approval message received in this iteration, preserved as the authorization record.

> I explicitly approve the following four decisions for Shift Bank Stage 4 OpenSpec.
>
> DECISION 1 — TLS: APPROVE.
>
> I authorize moving only the E4 dev-cert.pem and dev-key.pem files to:
>
> C:\Users\danie\AppData\Local\ShiftBank-E4\secrets\tls\
>
> Use restricted ACLs, preserve E3 and all historical evidence, and do not overwrite, disclose, regenerate, or rotate credentials.
>
> DECISION 2 — D-02: APPROVE.
>
> I approve:
> - Legacy currency: COP.
> - One-time simulated conversion: 4000 COP = 1 USD.
> - Retain internal IDs acc_checking and acc_savings.
> - Introduce public references CHK-1001 and SAV-2001 while preserving legacy compatibility.
> - Converted opening balances: USD 1250.00 and USD 3750.00 for the reported initial state.
> - EUR-3001 and GBP-4001 with zero opening balances.
> - Explicit deviation from D-02 reference balances.
> - Preservation of original transaction history, IDs, timestamps, monetary provenance, and audit integrity.
> - Deterministic migration-boundary snapshot without double-posting historical transactions.
> - Exact arithmetic and verifiable reconciliation.
> - No artificial balancing transactions.
> - Fail-closed behavior when financial invariants cannot be demonstrated.
>
> DECISION 3 — LEGACY STATES: APPROVE.
>
> Before migration, require:
> - No pending ACH transactions.
> - No pending MFA authorizations.
> - No active or paused recurring schedules requiring migration.
> - Zero current-day transfer-limit consumption.
>
> If any condition fails, abort migration without modifying financial state. Do not automatically resolve, cancel, settle, or convert pending obligations.
>
> Preserve historical terminal records.
>
> Document this limitation explicitly.
>
> DECISION 4 — H2: AUTHORIZE.
>
> I explicitly authorize creating and strictly validating native OpenSpec Stage 4 proposal, design, specification deltas, acceptance scenarios, and implementation tasks.
>
> Follow the approved D-01 through D-14 common contracts and the D-02-specific researcher-approved deviation.
>
> Use the native OpenSpec workflow.
>
> Record approval evidence, specification hashes, validation output, and traceability.
>
> Do not modify application code or tests.
> Do not execute financial migration.
> Do not deploy or run load tests.
> Do not modify Stage 3.
> Do not commit or archive OpenSpec changes.
>
> Once H2 specifications are generated and validated, STOP for my review and separate implementation approval.
