# High-Precision Web Calculator Application

A visually appealing, daily-use, fully accessible web calculator that calculates mathematical expressions with exact decimal precision, adhering strictly to standard PEMDAS precedence rules.

## Core Features
1. **Absolute Decimal Precision**: Powered by Python's built-in `decimal` module recursively evaluating whitelisted Abstract Syntax Trees (AST). Eliminates binary float arithmetic representational discrepancies (e.g. `0.1 + 0.2` returns `0.3` exactly).
2. **PEMDAS Parsing**: Full support for chained operators, custom decimal points, unary positives/negatives, and closed/nested parentheses.
3. **Accessibility (a11y)**: Built-in desktop-like tactile layout with comprehensive screen reader live region announcements (`aria-live="polite"`), descriptive ARIA label buttons, and complete document-level keyboard mappings.
4. **Clean Stateless REST Architecture**: Strict separation of concerns between React (TypeScript) and FastAPI (Python 3.11+).

---

## Testing & Quality Gates

Both frontend and backend test suites are configured to strictly verify all mathematical operations, keyboard events, and accessibility structures, and enforce a **$\ge 80\%$ statement and branch code coverage threshold**.

### Backend (Pytest + Pytest-Cov)
Run backend tests with automated statement/branch coverage reporting:
```bash
cd backend
# Run test runner (pyproject.toml loads the default coverage settings)
..\.venv\Scripts\python -m pytest
```

### Frontend (Vitest + JSDOM)
Run frontend tests and generate code coverage reporting:
```bash
cd frontend
# Execute test runner
npm run test:run

# Execute test suite with coverage report
npm run test:coverage
```

---

## Containerized Deployment & Orchestration

The application is fully containerized using multi-stage production Docker configurations that adhere to strict container security practices (such as running services under unprivileged non-root users). It uses Nginx unprivileged serving with a built-in reverse proxy routing `/api/` calls directly to the backend to eliminate CORS issues.

### Local Orchestration with Docker Compose

To build and launch both services networked together inside an isolated container network, run:
```bash
# Build secure images and start services
docker compose up --build
```

- **Frontend client**: Accessible on the host at `http://localhost:80` (internally mapped from unprivileged Nginx port `8080`).
- **Backend service**: Accessible on the host at `http://localhost:8000`.

To teardown the orchestrated services and clean up bridge network environments, run:
```bash
docker compose down --volumes
```

---

## Verification & Manual Auditing

For detailed step-by-step end-to-end verification and compliance auditing procedures, please refer to the [Quickstart & Verification Guide](./specs/003-testing-deployment/quickstart.md).
