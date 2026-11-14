# Production Dockerfile for FastAPI backend using Python 3.12
FROM python:3.12-slim

WORKDIR /app

# Copy production lock file
COPY requirements-prod.lock /app/requirements-prod.lock

# Install production dependencies using exact-pinned lockfile
RUN pip install --no-cache-dir -r requirements-prod.lock

# Copy only application source, completely omitting tests
COPY app/main.py /app/app/main.py
COPY app/core/ /app/app/core/

# Create unprivileged system user and group
RUN groupadd -g 10001 tetris && \
    useradd -u 10001 -g tetris -m -s /sbin/nologin tetris

# Create a designated writable directory for SQLite database storage and assign ownership
RUN mkdir -p /app/data && chown -R tetris:tetris /app

USER tetris

ENV TETRIS_DB_PATH=/app/data/high-scores.sqlite3
ENV PYTHONPATH=/app

EXPOSE 8000

# Healthcheck using uvicorn internal endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/high-scores')" || exit 1

# Run FastAPI backend using exactly one worker
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
