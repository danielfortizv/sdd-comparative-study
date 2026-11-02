# Backend container image for the web-calculator math oracle.
# Stage 3, Requirement 31: multi-stage, non-root, runtime-only final image.
#
# Stage 1 (builder): install the project's RUNTIME dependencies only (no [test]
# extra) into an isolated virtualenv at /opt/venv. Requirement 31.1, 31.5.
# Stage 2 (runtime): a minimal python:3.11-slim image (Requirement 31.2) that
# copies /opt/venv + the app/ package, runs as a created non-root appuser with a
# non-zero uid (Requirement 31.3), exposes a configurable port defaulting to 8000
# (Requirements 31.4, 31.6), and execs uvicorn as PID 1 so a startup failure
# propagates a non-zero exit code (Requirement 31.7).

# ---------------------------------------------------------------------------
# Stage 1: builder — build an isolated venv with runtime deps only.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# Create the isolated virtualenv and put it first on PATH so pip installs into it.
ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv "$VIRTUAL_ENV"

WORKDIR /build

# Copy only the files needed to resolve and install runtime dependencies. The
# project metadata + the app package are installed WITHOUT the [test] extra, so
# pytest/hypothesis/httpx never enter the image.
COPY pyproject.toml ./
COPY app ./app

# Install the project and its runtime dependencies (fastapi, uvicorn, pydantic)
# into /opt/venv. No "[test]" extra -> no build/test deps in the venv.
RUN pip install .

# ---------------------------------------------------------------------------
# Stage 2: runtime — minimal image, non-root, runtime deps + app only.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Make the copied venv the active interpreter environment.
ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Configurable listen port with a safe in-range default (Requirement 31.4).
    PORT=8000

# Create a non-root user with a non-zero uid and run as it (Requirement 31.3).
RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

# Copy the pre-built virtualenv (runtime deps only) and the application package.
# No test/build dependencies and no tests/ are copied (Requirement 31.5); the
# .dockerignore keeps them out of the build context entirely.
COPY --from=builder /opt/venv /opt/venv
COPY app ./app

# Drop privileges before declaring the entry point.
USER appuser

# Document the default port the service listens on (Requirement 31.6).
EXPOSE 8000

# exec form via a shell so ${PORT:-8000} is expanded at runtime while uvicorn
# still replaces the shell as PID 1 (via `exec`). An unset PORT falls back to
# 8000; a startup failure exits non-zero (Requirement 31.7).
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
