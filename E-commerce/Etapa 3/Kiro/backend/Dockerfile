# syntax=docker/dockerfile:1

# Multi-stage build for the FastAPI backend (Stage 3, Requirement 4.1).
#
# Stage 1 (builder) installs the pinned dependencies into an isolated
# virtualenv. Stage 2 (runtime) copies only that virtualenv and the application
# source onto a slim base, so the runtime image carries no build tooling.

# --- Stage 1: build dependencies ---------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Create a virtualenv and install the pinned requirements into it.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# --- Stage 2: slim runtime ----------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy the prepared virtualenv and the application source only.
COPY --from=builder /opt/venv /opt/venv
COPY app ./app

# The review-image folder is a local, git-ignored on-disk artifact (Stage 2).
# Ensure it exists in the image so image serving works out of the box.
RUN mkdir -p app/data/review_images

# Run as a non-root user for a safer default.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Serve the FastAPI app. The /health endpoint backs the Compose healthcheck.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
