# Technical Stack & Directory Layout Companion

This companion defines the engineering conventions, technical stack, directory layout, and verification commands for **Tetris Stage 1, Option A**.

## 1. Technical Stack

### Backend Stack
- **Language:** Python 3.11+
- **Web Framework:** FastAPI (with Pydantic v2 for schemas)
- **ASGI Server:** Uvicorn
- **Testing Framework:** Pytest (with HTTP testing support)
- **Code Style:** PEP 8 compliance, explicit type-hinting, strict English commenting.

### Frontend Stack
- **Language:** TypeScript
- **View Library:** React 18+
- **Build Tool:** Vite
- **Styling:** Vanilla CSS (no TailwindCSS as per local preferences)
- **HTTP Client:** Native `fetch` API

---

## 2. Directory Layout

The codebase must follow a strict greenfield structure inside the `backend/` and `frontend/` folders respectively, as requested. No files may be touched or created outside of these specified directories.

```text
/ (Project Root)
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI application & HTTP controllers
│   │   ├── models.py        # Pydantic state & input models
│   │   └── rules.py         # Authoritative board rules and collision engine
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py      # Test setup and client fixtures
│   │   └── test_rules.py    # Robust Pytest coverage for all 8 criteria
│   ├── requirements.txt     # Backend dependencies
│   └── README.md            # Backend instructions
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Game UI & canvas renderer
│   │   ├── App.css          # Vanilla CSS styling
│   │   ├── useTetris.ts     # Keyboard listener & gravity game loops
│   │   ├── main.tsx         # React root
│   │   └── vite-env.d.ts
│   ├── package.json         # Frontend dependencies
│   ├── vite.config.ts       # Vite bundler config
│   ├── tsconfig.json        # TypeScript configuration
│   └── README.md            # Frontend instructions
```

---

## 3. Run and Test Commands

### Backend

**Install dependencies:**
```bash
pip install -r backend/requirements.txt
```

**Run development server:**
```bash
uvicorn app.main:app --reload --port 8000
# Expected on: http://localhost:8000
```

**Run automated unit tests:**
```bash
pytest backend/
```

### Frontend

**Install dependencies:**
```bash
npm install
```

**Run development client:**
```bash
npm run dev -- --port 3000
# Expected on: http://localhost:3000
```

**Build production assets:**
```bash
npm run build
```
