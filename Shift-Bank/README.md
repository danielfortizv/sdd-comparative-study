# Banking System Case Study

The Banking System case represents a security-sensitive financial application. Its requirements progress from basic account operations to third-party payments, stronger security and audit controls, and a major change to the financial data model. The case matrix estimates more than 150 requirements. The implementations use a Python FastAPI backend and a React frontend with TypeScript.

## Development Progression

| Stage | Scope |
| --- | --- |
| Etapa 1 — Initialization | For a simulated authenticated user: view account balances, transfer funds between owned accounts, review transaction history, and perform simulated MFA for sensitive transfers. User registration and login are out of scope for this stage. |
| Etapa 2 — Functional complexity and state | Third-party and interbank ACH transfers, scheduled recurring payments, and dynamic limits. |
| Etapa 3 — Architecture, security, and CI/CD | End-to-end encryption of sensitive data, immutable transaction audit logs, load testing, and deployment. |
| Etapa 4 — Breaking change and migration | Add multi-currency accounts and conversion, and transition toward Event Sourcing/CQRS. |

## Run an Implementation

Etapa 1 contains OpenSpec and Spec Kit implementations. Run the backend and frontend in separate terminals. In each terminal, first change to the root of the selected implementation—the directory containing `backend/` and `frontend/`. For example, from this case directory:

```powershell
cd "Etapa 1/OpenSpec"
```

After changing to the selected implementation root, start the backend in one terminal:

```powershell
cd backend
python -m pip install -r requirements.txt
```

Then run the backend command for the selected tool:

| Tool | Backend command from `backend/` |
| --- | --- |
| OpenSpec | `uvicorn main:app --reload --port 8000` |
| Spec Kit | `uvicorn src.main:app --reload --port 8000` |

In a second terminal, again start at the selected implementation root, then start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Both frontends use Vite and listen on port 5173 by default. Run the installation commands once per implementation, then use the start commands for subsequent runs.
