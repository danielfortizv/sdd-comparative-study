# Shared multi-stage image for the Stage 4 Python services.
#
# The same image runs identity, commerce, reviews, or gateway; Compose selects
# which service by overriding the working directory and the uvicorn target port.
# Build stage installs pinned deps into a venv; the slim runtime copies the venv
# and the service source. No paid service and nothing deployed.

FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt
COPY contracts /build/contracts
# Install the shared contracts package non-editably so it is baked into the venv
# that the runtime copies. An editable install (`pip install -e`) would write an
# absolute finder mapping back to this build-time path (/build/contracts), which
# does not exist in the runtime image, breaking service imports.
RUN /opt/venv/bin/pip install /build/contracts

FROM python:3.11-slim AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/contracts /app/contracts
# Each service's source is copied in; Compose sets the working dir per service.
COPY identity /app/identity
COPY commerce /app/commerce
COPY reviews /app/reviews
COPY gateway /app/gateway
# Default to the gateway; Compose overrides working_dir + command per service.
WORKDIR /app/gateway
EXPOSE 18200
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "18200"]
