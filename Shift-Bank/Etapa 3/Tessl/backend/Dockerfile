FROM python:3.13-slim

WORKDIR /app

# Install curl for health check and create unprivileged application user
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -r appuser && \
    useradd -r -g appuser -u 1000 -d /app -s /sbin/nologin appuser

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ ./backend/app/
COPY run.py ./backend/

# Create directory for persistent SQLite database volume and configure permissions
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite:////app/data/shift_bank.db

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
