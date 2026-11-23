# Tetris Case Study

Tetris is a browser-based game case study focused on interactive state, timed updates, and increasingly complex gameplay. The case matrix estimates 25–40 requirements. The implementations use React with TypeScript for the frontend and a Python FastAPI backend that owns the authoritative game state and rules.

## Development Progression

| Stage | Scope |
| --- | --- |
| Etapa 1 — Initialization | Game grid, piece rendering and gravity, collision handling, and line clearing. |
| Etapa 2 — Functional complexity and state | Scoring, progressive levels and speed, a held piece, and a next-piece preview. |
| Etapa 3 — Architecture, security, and CI/CD | High-score persistence, automated quality checks, performance testing, and containerization. |
| Etapa 4 — Breaking change and migration | Replace the React DOM rendering approach with Canvas 2D/WebGL and add real-time multiplayer. |

Implementation directories are grouped by stage and tool. All five tools are represented in [`Etapa 1`](Etapa%201/README.md), [`Etapa 2`](Etapa%202/README.md), and [`Etapa 3`](Etapa%203). [`Etapa 4`](Etapa%204) contains OpenSpec, Spec Kit, Tessl, and Kiro. BMAD Method was outside the scope of Etapa 4.

## Run an Implementation

For Etapas 1 and 2, run the backend and frontend in separate terminals. In each terminal, first change to the root of the selected implementation, which contains `backend/` and `frontend/`. For example, from this case directory:

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

All five frontends use Vite and listen on port 5173 by default. Run the installation commands once per implementation, then use the start commands for subsequent runs.

### Etapas 3 and 4

Open a terminal in the selected implementation directory. With Docker and the Compose plugin running, build and start the services:

```powershell
docker compose up -d --build
```

For Kiro in Etapa 4, use its stage-specific Compose file:

```powershell
docker compose -f docker-compose.stage4.yml up -d --build
```

| Implementation | Browser URL |
| --- | --- |
| Etapa 3, all five tools | `http://localhost:5183` |
| Etapa 4, OpenSpec | `http://localhost:5514` |
| Etapa 4, Spec Kit | `http://localhost:5183` |
| Etapa 4, Tessl | `http://localhost:5515` |
| Etapa 4, Kiro | `http://localhost:5517` |

Stop the selected implementation with `docker compose down`, using the same `-f` option for Kiro Etapa 4. When switching variants, stop the previous one first if both use the same port. Omit `--volumes` to keep the local ranking data.
