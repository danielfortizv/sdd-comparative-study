# Stage 1: Build virtual environment
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Production runtime image
FROM python:3.11-slim AS runner

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root system user
RUN groupadd -g 10001 appgroup && \
    useradd -r -u 10001 -g appgroup -d /app -s /sbin/nologin appuser

# Copy application source
COPY backend/ /app/backend

# Create database directory and set correct owner permissions
RUN mkdir -p /app/data && chown -R appuser:appgroup /app

# Switch to non-root user
USER 10001

# Environment variables
ENV PORT=8000
ENV HOST=0.0.0.0
ENV TETRIS_DB_PATH=/app/data/high-scores.sqlite3
ENV PYTHONUNBUFFERED=1

# Expose internal API port
EXPOSE 8000

# Healthcheck using python to check endpoint status without requiring curl
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/high-scores')" || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
