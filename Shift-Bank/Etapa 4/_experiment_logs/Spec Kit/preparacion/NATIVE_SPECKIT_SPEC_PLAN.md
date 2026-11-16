# Proposed Native Spec Kit Specification Plan — Researcher Review Only

**Proposal only.** This is preparation evidence, not a functional specification. It must not be placed under `Etapa 4/Spec Kit/specs/` or counted in D3. No Gate A approval has been granted.

## Existing artifacts to preserve and consult

- `specs/001-shift-bank-stage1/` and `specs/002-shift-bank-stage2/` — inherited behaviors and acceptance.
- `specs/003-shift-bank-stage3/` — encrypted transport/storage, audit, Locust, deployment, and regression baseline.
- `.specify/memory/constitution.md`, `.specify/templates/`, `.specify/workflows/`, `.gemini/commands/` — native Spec Kit and current integration workflow.

Do not edit these inherited artifacts during Stage 4 discovery. The Stage 3 spec currently says `Draft` while acceptance documents claim completion; obtain researcher direction on this baseline status.

## Proposed E4 native artifacts after Gate A

Use the native Spec Kit workflow to propose one new feature directory, e.g. `specs/004-shift-bank-stage4-multicurrency-eventsourcing-cqrs/`, containing the tool-native `spec.md`, clarification record, plan, research, data model, API contracts, quickstart, tasks, and acceptance checklist as appropriate. These are proposed artifact types only; no directory or functional spec has been created.

| Area | Proposed coverage / acceptance evidence | E3 compatibility risk requiring explicit approval |
|---|---|---|
| Currency-aware accounts and histories | Currency identity on balances and entries; verify seeded/migrated legacy state exactly. | COP seed IDs/values vs D-02 USD/EUR/GBP account contract. |
| FX conversion | Transparent source/destination amounts, rate, exact arithmetic/rounding, conversion history, conservation and failure/retry cases. | Rates, fees, precision, supported currencies, and conversion of COP are unapproved. |
| Event sourcing | Durable domain-event boundaries, append-only persistence, migration, replay, idempotency, and distinction from HMAC audit records. | E3 audit logs are not interchangeable with a monetary domain-event store. |
| CQRS | Command/query separation, projection update consistency, deterministic rebuild, version conflicts, failure behavior. | Storage design and consistency guarantees require decisions; avoid prescribing an unapproved event-store technology. |
| Inherited workflows/security | Internal transfer, ACH settlement/refund, recurring, dynamic limits, MFA, encryption, audit, and deployment behavior. | D-07 USD-equivalent limits/MFA conflict; D-08 currency restrictions alter inherited flows. |
| Cross-stage acceptance | Migration/no-value-change checks, retries/idempotency, no double debit/credit, projection replay, and Stage 1–3 regressions. | Must use a researcher-approved baseline and safely isolated test resources. |

## Proposed acceptance mapping

Map the supplied common REQ-01–REQ-06 to explicit Given/When/Then scenarios: currency-labelled balances/history; exact FX; durable event replay distinct from audit; deterministic projections; inherited workflows/security with approved currency rules; and migration/retry/failure/regression evidence. Keep optional implementation extras outside the minimum contract and report separately.

## Gate sequence

1. **Gate A:** researcher supplies missing authoritative materials, confirms the exact E3 snapshot and measured agent/model, resolves COP/USD/D-01/D-02/D-07 semantics, and approves this plan.
2. Only after Gate A, the measured agent may use the native Spec Kit clarification/specification workflow. Save approved decisions and spec hashes; stop for review.
3. **Gate B:** a separate explicit researcher approval is required after review of the proposed specs and tasks. No implementation before Gate B.
