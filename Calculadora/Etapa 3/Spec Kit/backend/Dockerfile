# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .

# Install dependencies into a wheels directory
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Minimal runtime stage
FROM python:3.11-slim AS runtime

WORKDIR /app

# Create a system group and non-root appuser with UID/GID 10001
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -s /bin/sh -m appuser

# Copy installed libraries from the builder stage
COPY --from=builder /root/.local /home/appuser/.local
COPY . /app

# Ensure correct files permissions
RUN chown -R appuser:appuser /app /home/appuser

# Add local path to PATH environment variable
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Expose port and switch to the non-root user
EXPOSE 8000
USER appuser

# CMD to start the FastAPI server
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
