# Spec Kit — Stage 1 Shared Environment

## Workspace

- Project: Shift Bank
- Comparative-study stage: Stage 1
- Working directory: `Etapa 1/Spec Kit`
- Git branch: `001-shift-bank-stage1` during the feature workflow; later repository checkpoint branch recorded as `ShiftBank`.
- OS: Windows AMD64
- Shell: Windows PowerShell

## Specification workflow

- SDD framework: GitHub Spec Kit
- Spec Kit CLI: 1.0.6
- Agent integration: Gemini CLI
- Gemini CLI: 0.60.0
- Script type: PowerShell (`ps`)
- Constitution final version: 1.2.0

## Application baseline

- Backend: Python 3.13 + FastAPI
- Persistence: native SQLite via `sqlite3`
- Monetary arithmetic: `decimal.Decimal`
- Frontend: React + TypeScript + Vite
- Styling: Vanilla CSS
- Development communication: FastAPI `CORSMiddleware` with Vite origin `http://localhost:5173`
- MFA: fixed mock code `123456`; no external MFA service

## Validation environment

- Python: 3.13.2
- Node.js: 20.17.0
- Vitest: project-configured test runner
- Ruff: backend lint/format validation
- SonarQube Community Build: 26.9.0.129388
- SonarScanner CLI: 8.1.0.6389
- SonarQube project key: `shift-bank-stage1-openspec`
- SonarQube deployment: Docker on port 9000

## Validation policy

Automated evidence is recorded separately from human browser evidence. SonarQube is retained as a final static-analysis evidence source, but its Community Build security-analysis limitations are documented alongside its results.

T036 is not considered complete until the canonical `quickstart.md` manual scenarios have been executed by a human and evidenced.
