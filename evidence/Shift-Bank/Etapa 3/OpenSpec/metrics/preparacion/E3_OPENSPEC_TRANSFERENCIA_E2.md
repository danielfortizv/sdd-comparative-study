# Stage 2 to Stage 3 OpenSpec transfer

## Effective inherited requirements

The implementation comes from the active `stage2-banking-enhancements` change in `Etapa 3/OpenSpec/openspec/changes/`. The four main specs under `openspec/specs/` are Stage 1 contracts only. The complete effective contract therefore combines those main specs with all seven Stage 2 delta specs (bank accounts, MFA, transaction history, transfers, ACH transfers, transfer limits, and recurring payments), plus the Stage 2 proposal/design and completed task checklist. Stage 2 remains active and unsynchronized, by design.

## Architecture and behavior observed

- FastAPI backend uses direct SQLite persistence. `database.py` selects `SHIFT_BANK_DB` or defaults to `backend/bank.db`, initializes tables repeatably, and maintains accounts, internal transactions, limits, beneficiaries, ACH transfers, recurring schedules, and occurrences.
- `banking.py` centralizes exact COP validation, transaction/limit enforcement, simulated MFA, ACH state transitions, and schedule processing. Sensitive operations use the inherited fixed simulated MFA code and five-minute window; the Stage 2 contract says the threshold is COP 1,000,000.
- Internal transfers, ACH acceptance/refund, and recurring executions mutate persisted financial state. ACH captures recipient details, debits at acceptance, settles normally after 30 seconds, and supports deterministic internal failure simulation/refund. Recurring processing uses anchored UTC cadence and restart recovery.
- `main.py` starts an application-owned background processor in FastAPI lifespan to expire MFA and process ACH/schedules. This has implications for multi-worker deployment and process lifecycle.
- React/TypeScript frontend presents accounts, history, internal and ACH transfer flows, MFA, beneficiaries, limits, recurring schedules, and polling refresh.

## Limitations and compatibility cautions

- SQLite schema contains account balances, transactions, bank account identifiers, beneficiary routing/account numbers, ACH recipient snapshots, schedule terms, and MFA-related states. Stage 3 must define which fields are sensitive and how they remain queryable without weakening existing behavior.
- The current mock user is already authenticated; no real login or identity boundary exists. End-to-end encryption needs a concrete sender/recipient trust boundary and threat model before it can be specified meaningfully.
- SQLite is a single-file persistence model. Audit tamper resistance, backup/restore, concurrent workers, and deployment durability cannot be assumed from the current implementation.
- Stage 2 final inventory preserves hashes and sizes, not complete Stage 1 file contents. Its closure reports partially unverified manual checks and unavailable issue-level SonarQube findings.
- Final Stage 2 telemetry reports Codex rather than planned Gemini, observed OpenSpec 1.11.0 (preparation noted 1.9.0), and no reliable total token/cost/call/session metrics.
