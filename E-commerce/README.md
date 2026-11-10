# E-commerce Case Study

The E-commerce case studies a data-oriented web application with a product catalog, shopping cart, authentication, and checkout. Its progression introduces increasingly complex inventory, payment, quality assurance, and architecture requirements. The case matrix estimates 60–100 requirements. Implementations use a Python FastAPI backend and a React frontend with TypeScript.

## Development Progression

| Stage | Scope |
| --- | --- |
| Etapa 1 — Initialization | Product catalog, local shopping cart, simulated checkout, and basic authentication. |
| Etapa 2 — Functional complexity and state | Real-time inventory management, discount coupons, multi-criteria filters, and a simulated payment gateway. |
| Etapa 3 — Architecture, security, and CI/CD | End-to-end tests, automated pipeline, multi-stage container, and API caching. |
| Etapa 4 — Breaking change and migration | Migrate from a monolith to a microservices and event-driven architecture. |

The implementation directory is named `Etapa-1` and contains independent versions for the five SDD tools. The run instructions below target this directory.

## Run an Implementation

Run the backend and frontend in separate terminals. In each terminal, first change to the root of the selected implementation—the directory containing `backend/` and `frontend/`. For example, from this case directory:

```powershell
cd "Etapa-1/Bmad Method"
```

From `backend/`, use the matching command:

```powershell
cd backend
python -m pip install -r requirements.txt
```

Then start the backend with the command for the selected tool:

| Tool | Backend command |
| --- | --- |
| BMad Method | `uvicorn main:app --reload --port 8000` |
| Spec Kit | `uvicorn src.main:app --reload --port 8000` |
| Kiro, OpenSpec, Tessl | `uvicorn app.main:app --reload --port 8000` |

In a second terminal, again start at the selected implementation root and run the following once from `frontend/` to install the frontend dependencies:

```powershell
cd frontend
npm install
```

Then start the frontend with the selected tool's command:

| Tool | Frontend command | Default address |
| --- | --- | --- |
| BMad Method, Kiro | `npm run dev` | `http://localhost:5173` |
| OpenSpec | `npm run dev` | `http://127.0.0.1:5173` |
| Tessl | `npm run dev` | `http://localhost:3000` |
| Spec Kit | `npm start` | `http://localhost:3000` |

Run each installation command once per implementation, then use the service start commands for subsequent runs.
