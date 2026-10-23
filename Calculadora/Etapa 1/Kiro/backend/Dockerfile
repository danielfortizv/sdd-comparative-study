# syntax=docker/dockerfile:1

# Backend image (Requirement 31): multi-stage, non-root, minimal Python base,
# runtime-only dependencies. Stage 3 task 45.

# --- Stage 1: builder ---
FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
# Runtime deps only (no [test] extra) so pytest/hypothesis never reach runtime (31.5).
COPY pyproject.toml ./
COPY app ./app
RUN pip install .

# --- Stage 2: runtime ---
FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH" PORT=8000
# Non-root user, uid != 0 (31.3).
RUN useradd --create-home --uid 1001 appuser
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/app /app/app
USER appuser
EXPOSE 8000
# exec form => uvicorn is PID 1, so a startup failure exits non-zero (31.7);
# ${PORT:-8000} keeps the port configurable with an in-range default (31.4, 31.6).
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
