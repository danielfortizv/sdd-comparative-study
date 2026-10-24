# ==============================================================================
# Stage 1: Build dependencies & wheels
# ==============================================================================
FROM python:3.13-slim AS builder

WORKDIR /build

# Install system utilities needed for building wheels if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Create wheel files for all dependencies to keep the final image clean
RUN pip install --no-cache-dir --user -r requirements.txt

# ==============================================================================
# Stage 2: Final minimal execution container
# ==============================================================================
FROM python:3.13-slim AS runner

WORKDIR /app

# Prevent Python from writing .pyc files to disk and ensure direct console logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a secure, non-privileged system user/group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh appuser

# Copy installed dependencies from Stage 1
COPY --from=builder /root/.local /home/appuser/.local
COPY . /app

# Fix directory ownership for app user
RUN chown -r appuser:appgroup /app

# Put user local path in python path
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app

USER appuser

EXPOSE 8000

# Start server safely
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
