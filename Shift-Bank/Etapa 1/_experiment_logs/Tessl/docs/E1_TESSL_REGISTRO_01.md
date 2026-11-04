# Tessl — Stage 1 — Initial Implementation Record

## Experimental Configuration

- Case study: Shift Bank (Banking Application).
- Stage: 1 — Initialization and Base Requirements.
- SDD tool: Tessl CLI 0.118.1.
- Installed SDD plugin: `tessl-labs/spec-driven-development@2.0.1`.
- AI agent: Gemini CLI.
- Model displayed during execution: `gemini-3.5-flash`.
- Gemini CLI version verified before the experiment setup: 0.65.0. The version actually used during implementation was not captured in the provided session transcript.
- Initial prompt: `SEED-1.md`.
- Operating system: Windows.
- Backend: Python 3.13.2, FastAPI, SQLAlchemy, SQLite.
- Frontend: React, TypeScript, Vite.
- Testing frameworks: Pytest, Vitest, React Testing Library.

## 1. Requirements Gathering

The agent activated Tessl's `requirement-gathering` skill before generating specifications.

Six clarification questions were answered:

1. Sensitive transfer threshold: strictly greater than USD 1,000.
2. MFA mechanism: mock Security PIN.
3. Backend architecture: FastAPI with SQLite.
4. Initial accounts: Checking and Savings, denominated in USD.
5. PIN validation: `1234`, with lockout after three consecutive incorrect attempts.
6. Transaction history: individual account filters and an All Accounts view.

The agent proposed a consolidated requirements summary, including a single authenticated mock user, Alex Morgan, and two initial accounts with balances of USD 2,500 and USD 10,000.

The requirements summary received explicit human approval before specification authoring.

## 2. Specification Generation

The agent activated Tessl's `spec-writer` skill and created four specifications:

| Specification | Initially reported lines |
|---|---:|
| `specs/accounts.spec.md` | 53 |
| `specs/transfers.spec.md` | 72 |
| `specs/transactions.spec.md` | 53 |
| `specs/mfa.spec.md` | 57 |
| **Total** | **235** |

Initial documentation density: 58.75 lines per specification file.

These counts originate from the initial WriteFile operations recorded in the Gemini transcript; they are not a separate filesystem recount.

Each specification contained YAML frontmatter, target file references, behavioral requirements, and `[@test]` references.

A second explicit human approval was recorded after specification generation and before implementation.

## 3. Implementation

The agent implemented the backend and frontend using the approved specifications.

Backend components included database models for User, Account, Transfer, Transaction, and MfaState, along with API routes and business services.

Frontend components included account summaries, internal transfers, transaction history, mock MFA verification, navigation, and an API client.

The agent also generated automated backend and frontend tests.

## 4. Automated Validation

Backend test command:

`python -m pytest backend/tests -v`

Final reported result: **19 passed, 1 warning**.

Frontend test command:

`npm run test`

Final reported result: **21 passed, 4 test files passed**.

Production build command:

`npm run build`

The first build failed because of an unused variable in `TransferModal.tsx`. After the agent removed that variable, the production build completed successfully.

Total final automated test results reported: **40 passed**.

These results demonstrate successful execution of the existing tests, not independent confirmation of complete functional coverage.

## 5. Agent Self-Corrections

Two source-code corrections are visible in the transcript:

1. `frontend/src/api/types.ts`: corrected an invalid TypeScript type, `str`, to `string`.
2. `frontend/src/components/TransferModal.tsx`: removed the unused `destinationAccount` variable following a TypeScript compilation error.

Both corrections were performed autonomously by the agent.

No explicit human-requested post-implementation correction appears in the provided transcript.

## 6. Observable Tool Activity

Visible tool invocation counts extracted from the supplied terminal transcript:

| Operation | Invocations |
|---|---:|
| ReadFile | 13 |
| WriteFile | 45 |
| Edit | 2 |
| Shell | 12 |
| Ask User | 8 |
| Activate Skill | 4 |
| FindFiles | 2 |
| **Total visible invocations** | **86** |

These are counts of visible operations, not authoritative Gemini CLI session statistics. The final quantitative analysis must use session telemetry to determine total tool calls, messages, token consumption, and processing time.

## 7. Tessl Workflow

The following four Tessl skills were activated during the session:

1. `requirement-gathering`
2. `spec-writer`
3. `spec-verification`
4. `work-review`

The agent reported that specification targets and linked tests existed and that no undocumented behavioral drift was detected. This was an agent-reported conclusion, not an independently reproduced audit.

## 8. Measurement Boundaries

The initial implementation record does not establish token totals, token cache utilization, financial cost, total processing time, static code quality metrics, test coverage percentage, or visually verified user-interface quality.

Those measurements require their corresponding raw session exports, CLI statistics, source-code measurements, SonarQube reports, or observed application behavior.

This document records only the initial execution checkpoint. Subsequent measurements and corrective iterations must be preserved as separate records without rewriting this checkpoint.