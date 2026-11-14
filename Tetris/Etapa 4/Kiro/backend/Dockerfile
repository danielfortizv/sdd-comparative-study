# Multi-stage backend image (Stage 3, Option A).
#
# Build stage installs ONLY the production runtime dependency set into a venv;
# the slim runtime stage copies that venv and the app. Dev/test/audit packages
# (pytest, httpx, pytest-cov, pip-audit) are NEVER installed into the runtime
# image. Runs as a non-root user and starts exactly one uvicorn worker.

# ---- build stage ----
FROM python:3.12-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Create an isolated virtual environment for the runtime dependencies.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install ONLY the production runtime set from the RESOLVED runtime lock
# (every transitive pinned); NO dev/test/audit packages. The input manifest
# requirements.txt is copied for provenance but the lock is the install target.
COPY requirements.txt requirements.lock.txt ./
RUN pip install --upgrade pip && pip install --no-deps -r requirements.lock.txt

# ---- runtime stage ----
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    TETRIS_DB_PATH=/data/high-scores.sqlite3

# Create a non-root user and a writable data directory on the volume mount.
RUN groupadd --system tetris && \
    useradd --system --gid tetris --home-dir /app --no-create-home tetris && \
    mkdir -p /data && chown -R tetris:tetris /data

WORKDIR /app

# Copy the runtime venv and the application source only.
COPY --from=build /opt/venv /opt/venv
COPY app ./app

USER tetris

EXPOSE 8000

# Container health check hits the liveness endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

# Exactly one worker; the in-memory game store is single-process.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
