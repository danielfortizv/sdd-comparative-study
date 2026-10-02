# Spec Kit — Stage 1 Experiment Metadata

## Experiment

- Project: Shift Bank
- Stage: Stage 1
- SDD tool: GitHub Spec Kit
- Spec Kit CLI: 1.0.6
- AI integration: Gemini CLI
- Gemini CLI version: 0.60.0
- Integration configured with: `--integration gemini`
- Script type: PowerShell (`ps`)
- Platform: Windows / AMD64
- Python: 3.13.2
- uv: 0.12.21
- Shell: Windows PowerShell
- Git feature branch: `001-shift-bank-stage1`
- Project workspace: `Etapa 1/Spec Kit`
- Feature directory: `specs/001-shift-bank-stage1`

## Experimental objective

Evaluate a specification-driven development workflow for Shift Bank Stage 1, with emphasis on:

1. How much human correction is required in specifications and planning artifacts.
2. How closely implementation follows approved artifacts.
3. How much application code is changed during implementation.
4. Validation quality and evidence produced by the workflow.
5. Time and interaction cost of the AI-assisted workflow.

## Approved Stage 1 baseline

- Currency: COP only.
- Exactly two accounts: Checking and Savings.
- Initial balances: COP 5,000,000 and COP 15,000,000.
- Transfers only between the user's own two accounts.
- No overdrafts, non-positive amounts, or same-account transfers.
- Exactly two pre-seeded historical transfers:
  - COP 500,000 from Savings to Checking.
  - COP 100,000 from Checking to Savings.
- History shows direction, date, amount, and description; no resulting-balance column.
- Sensitive transfer threshold: >= COP 1,000,000.
- Fixed mock MFA code: `123456`.
- MFA states: `PENDING_MFA`, `COMPLETED`, `FAILED`, `EXPIRED`.
- Pending MFA expires after five minutes.
- Source balance is revalidated at MFA confirmation.
- No MFA lockout.
- Application state is persistently stored server-side.

## Implementation baseline

The approved planning artifacts selected:

- Python 3.13 + FastAPI backend.
- Native SQLite persistence using `sqlite3`.
- React + TypeScript + Vite frontend.
- Vanilla CSS.
- Python `decimal.Decimal` for monetary arithmetic.
- FastAPI `CORSMiddleware` for local frontend/backend communication.
- No ORM, external MFA service, external proxy, scheduler, or background worker.

## Tool setup verification

`specify check` reported that the Specify CLI was ready to use and detected Gemini CLI and Visual Studio Code as available tools.

Spec Kit was initialized in an existing workspace containing empty `backend/` and `frontend/` directories. The first non-interactive initialization stopped because the directory was non-empty; initialization was then repeated with `--force` and succeeded. See `08_infrastructure_events.md`.
