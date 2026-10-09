# High-Precision Web Calculator Application

A visually appealing, daily-use, fully accessible web calculator that calculates mathematical expressions with exact decimal precision, adhering strictly to standard PEMDAS precedence rules.

## Core Features
1. **Absolute Decimal Precision**: Powered by Python's built-in `decimal` module recursively evaluating whitelisted Abstract Syntax Trees (AST). Eliminates binary float arithmetic representational discrepancies (e.g. `0.1 + 0.2` returns `0.3` exactly).
2. **PEMDAS Parsing**: Full support for chained operators, custom decimal points, unary positives/negatives, and closed/nested parentheses.
3. **Accessibility (a11y)**: Built-in desktop-like tactile layout with comprehensive screen reader live region announcements (`aria-live="polite"`), descriptive ARIA label buttons, and complete document-level keyboard mappings.
4. **Clean Stateless REST Architecture**: Strict separation of concerns between React (TypeScript) and FastAPI (Python 3.11+).

---

## Quickstart

### Backend Setup (FastAPI)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

### Frontend Setup (React SPA)
```bash
cd frontend
npm install
npm run dev
```

---

## Running Automated Tests

To run the backend mathematical evaluation and contract endpoint test suite:
```bash
$env:PYTHONPATH="backend"
backend/.venv/Scripts/python -m pytest backend/tests
```
