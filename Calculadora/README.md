# Calculator Case Study

The Calculator case begins as a small client-server web application and grows from basic arithmetic into a more complex scientific calculator. It provides a baseline for comparing setup overhead, specification handling, and the tools' ability to evolve an existing implementation. The case matrix estimates 10–15 requirements. The implementations use a Python backend with FastAPI and a React frontend with TypeScript.

## Development Progression

| Stage | Scope |
| --- | --- |
| Etapa 1 — Initialization | Basic arithmetic, order of operations, and a calculator display with a numeric keypad. |
| Etapa 2 — Functional complexity and state | Memory operations, session history, and advanced mathematical functions. |
| Etapa 3 — Architecture and quality | Unit tests and edge cases, Docker packaging, and continuous integration. |
| Etapa 4 — Breaking change and migration | Change the expression evaluation engine between abstract syntax tree (AST) and reverse Polish notation (RPN) representations. |

Each stage contains independent implementations by the available SDD tools. Select the stage and tool directory before starting either service.

## Run an Implementation

Run the backend and frontend in separate terminals. In each terminal, first change to the root of the selected implementation—the directory containing `backend/` and `frontend/`. For example, from this case directory:

```powershell
cd "Etapa 1/Bmad Method"
```

After changing to the selected implementation root, start the backend in one terminal:

```powershell
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

For **Spec Kit**, use its `src.main` module instead:

```powershell
cd backend
python -m pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

In a second terminal, again start at the selected implementation root and start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

These backend and frontend commands apply to Etapas 1–4. Frontend ports vary by tool: BMad Method and Spec Kit use port 3000; Kiro, OpenSpec, and Tessl use port 5173. Run the installation commands once per implementation, then use the start commands for subsequent runs.

For Etapas 3 and 4, each implementation also includes a Docker Compose configuration. From the implementation root, both services can be started with:

```powershell
docker compose up --build
```
