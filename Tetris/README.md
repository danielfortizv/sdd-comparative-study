# Tetris Case Study

Tetris is a browser-based game case study focused on interactive state, timed updates, and increasingly complex gameplay. The case matrix estimates 25–40 requirements. The implementations use React with TypeScript for the frontend and a Python FastAPI backend that owns the authoritative game state and rules.

## Development Progression

| Stage | Scope |
| --- | --- |
| Etapa 1 — Initialization | Game grid, piece rendering and gravity, collision handling, and line clearing. |
| Etapa 2 — Functional complexity and state | Scoring, progressive levels and speed, a held piece, and a next-piece preview. |
| Etapa 3 — Architecture, security, and CI/CD | High-score persistence, automated quality checks, performance testing, and containerization. |
| Etapa 4 — Breaking change and migration | Replace the React DOM rendering approach with Canvas 2D/WebGL and add real-time multiplayer. |

The repository contains implementation directories for Etapas 1 and 2. The stage reports and shared acceptance materials remain available in [`Etapa 1/`](Etapa%201/README.md) and [`Etapa 2/`](Etapa%202/README.md). The [`Etapa 2 advisor script`](Etapa%202/shared/report/guion-tetris-etapa2-asesor.md) accompanies the stage report.

## Run an Implementation

Run the backend and frontend in separate terminals. In each terminal, first change to the root of the selected implementation—the directory containing `backend/` and `frontend/`. For example, from this case directory:

```powershell
cd "Etapa 1/Kiro"
```

After changing to the selected implementation root, start the backend in one terminal:

```powershell
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

For **OpenSpec**, the FastAPI application is at the backend root, so use:

```powershell
cd backend
python -m pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

In a second terminal, again start at the selected implementation root and start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

These commands apply to both Etapa 1 and Etapa 2. All five frontends use Vite and listen on port 5173 by default. Run the installation commands once per implementation, then use the start commands for subsequent runs.
