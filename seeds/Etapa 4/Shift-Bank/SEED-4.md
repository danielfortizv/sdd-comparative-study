# SEED-4 — Shift Bank — Stage 4 (Option A)

## Existing application and migration context

Evolve the existing Shift Bank web application from each tool's own completed Stage 3 implementation. This is a disruptive change to an existing banking model and architecture, not a new application or a feature built from scratch.

Keep the established Python backend (FastAPI) and React/TypeScript frontend. The application serves an already authenticated mock user; real banking integrations, user registration, and login remain outside scope.

Preserve the behavior and applicable safeguards inherited from earlier stages: account balances and transaction history, internal transfers and simulated MFA; simulated third-party ACH/interbank transfers, recurring payments, and dynamic transfer limits; and Stage 3 sensitive-data encryption, immutable transaction audit records, load-testing artifacts, and deployment capabilities. Adapt their data contracts where the approved multicurrency migration requires it, without silently removing existing functionality.

## Stage 4 objective — Multicurrency accounts, conversion, and Event Sourcing/CQRS

1. **Multicurrency accounts.** Transition the banking model so accounts and monetary amounts have explicit currency identities. Users must be able to view balances and transaction histories with unambiguous currencies. Existing account state must be migrated or reconstructed without silently changing its monetary value.
2. **Currency conversion.** Support simulated conversions between supported currencies, exposing the rate applied, source amount and currency, destination amount and currency, and the resulting transaction records. Define and consistently enforce monetary precision, rounding, and balance-conservation rules. Do not assume an external live exchange-rate service is required.
3. **Event Sourcing.** Introduce an event-sourced approach for the monetary account/transaction domain, in which durable domain events record state transitions and enable reconstruction of the relevant account state. The event history must not be confused with, or substituted by, the inherited Stage 3 audit log. Define the event boundaries and how existing state transitions are migrated or represented.
4. **CQRS.** Separate the model/handling of state-changing banking commands from the model/handling of balance and transaction queries. Establish how read projections are derived, refreshed, and rebuilt from events, with observable behavior that remains compatible with the application's banking workflows.
5. **Cross-stage compatibility.** Preserve the validity and security of internal transfers, simulated ACH transfers, recurring schedules, dynamic transfer limits, mock MFA, encryption, and auditability under the new currency-aware model. Prevent unintended double debits, double credits, duplicate event application, and inconsistent balances. Document any feature whose cross-currency semantics require an explicit decision.
6. **Verifiability.** Specify testable acceptance scenarios for conversions, monetary invariants, event persistence/replay, projection correctness, migration of inherited state, failure and retry behavior, and regression of existing features. Do not claim that preexisting tests pass unless their results have been observed.

## Decisions to clarify before implementation

Clarify material ambiguities with the researcher before finalizing specifications: supported currencies and account-creation rules; exchange-rate source and update policy; fees, decimal precision, and rounding; whether and how internal transfers, ACH, recurring payments, and transfer limits work across currencies; the scope and persistence of domain events; migration and rollback of existing balances; projection consistency/rebuild strategy; failure handling and idempotency; and compatibility with existing encryption, audit, and deployment constraints.

Do not prescribe a specific database, message broker, cloud vendor, FX API, or event-store library unless the researcher explicitly approves that decision. The goal is an equivalent, verifiable functional and architectural outcome across the five SDD tools, while allowing each tool to follow its own specification workflow.
