# Stage 1: Build dependencies and wheels
FROM python:3.11-slim AS builder

WORKDIR /build

# Install compilation tools if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime image
FROM python:3.11-slim AS runner

WORKDIR /app

# Create a non-root group and user
RUN groupadd -g 10001 tetris && \
    useradd -r -u 10001 -g tetris -m -d /home/tetris tetris

# Copy installed packages from builder
COPY --from=builder /root/.local /home/tetris/.local
COPY app/ /app/app/

# Environment variables
ENV PATH=/home/tetris/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TETRIS_DB_PATH=/app/data/high-scores.sqlite3

# Create writable data directory and set permissions
RUN mkdir -p /app/data && \
    chown -R tetris:tetris /app

# Switch to the non-root user
USER tetris

EXPOSE 8000

# Run with exactly 1 worker as in-memory state is single-process restricted
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
