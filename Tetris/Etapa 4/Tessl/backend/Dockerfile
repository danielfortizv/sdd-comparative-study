# Stage 1: Build virtual environment
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install pinned uv to perform rapid, reproducible dependency installations
COPY --from=ghcr.io/astral-sh/uv:0.12.20 /uv /uv/bin/uv

# Copy dependency files and source code
COPY pyproject.toml uv.lock README.md ./
COPY app ./app

# Install production dependencies only using the genuine lockfile
RUN /uv/bin/uv sync --frozen --no-dev

# Stage 2: Runtime image
FROM python:3.12-slim AS runner

WORKDIR /app

# Create non-root user (UID 10001)
RUN groupadd -g 10001 tetris && \
    useradd -r -u 10001 -g tetris tetris

# Copy virtual environment and application files
COPY --from=builder /app/.venv /app/.venv
COPY app /app/app

# Create data directory for SQLite with correct permissions for non-root user
RUN mkdir -p /app/data && chown -R tetris:tetris /app/data

ENV PATH="/app/.venv/bin:$PATH"
ENV TETRIS_DB_PATH="/app/data/high-scores.sqlite3"

USER tetris

EXPOSE 8000

# Run with single worker to enforce single-process in-memory consistency
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
