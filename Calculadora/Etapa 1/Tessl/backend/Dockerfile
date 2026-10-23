# Multi-stage production Dockerfile for the FastAPI backend
# Stage 1: Dependency builder
FROM python:3.13-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Minimal security-hardened runtime environment
FROM python:3.13-slim AS runner

WORKDIR /app

# Ensure we adhere to security practices with a dedicated non-root user
RUN groupadd -r -g 10001 appgroup && \
    useradd -r -u 10001 -g appgroup -m -s /sbin/nologin appuser

# Copy installed python dependencies from builder stage
COPY --from=builder /root/.local /home/appuser/.local
COPY app /app/app

# Transfer ownership of directories to non-root user
RUN chown -R appuser:appgroup /app /home/appuser

# Configure environment paths
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/evaluate', data=b'{}')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
