# Stage 1: Build stage
FROM python:3.11-slim AS builder

WORKDIR /build

# Set environment variables to optimize python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install dependencies into a virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final runtime stage
FROM python:3.11-slim AS runner

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /bin/bash appuser

# Set working directory ownership to appuser
RUN chown appuser:appgroup /app

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application source
COPY --chown=appuser:appgroup app/ app/

# Switch to non-root user
USER appuser

# Expose backend port
EXPOSE 8005

# Run backend application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]
