import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.app.database import engine, Base, SessionLocal
from backend.app.routers import (
    accounts,
    transfers,
    transactions,
    beneficiaries,
    limits,
    recurring,
    crypto,
    audit,
    conversions,
)
from backend.app.services.account_service import seed_initial_data
from backend.app.services.transfer_service import MfaRequiredException
from backend.app.services.scheduler import start_background_scheduler, stop_background_scheduler
from backend.app.services.crypto_service import validate_encryption_key_at_startup
from backend.app.services.audit_service import validate_audit_key_at_startup
from backend.app.services.migration_service import run_migration, run_stage4_event_sourcing_migration
from backend.app.services.projection_service import verify_or_rebuild_at_startup


def validate_admin_key_at_startup() -> None:
    admin_key = os.getenv("ADMIN_SECRET_KEY")
    if not admin_key:
        if os.getenv("TESTING", "false").lower() == "true":
            return
        raise RuntimeError("ADMIN_SECRET_KEY environment variable is missing or empty")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate cryptographic configurations at startup (fails fast if invalid)
    validate_encryption_key_at_startup()
    validate_audit_key_at_startup()
    validate_admin_key_at_startup()

    # Initialize database tables and seed data
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_initial_data(db)
        # Execute idempotent encryption migration for legacy records
        migration_res = run_migration(db)
        if not migration_res.success:
            raise RuntimeError(
                f"Startup halted: encryption migration failed: {migration_res.error_message}"
            )
        # Execute Stage 4 Event Sourcing and Multicurrency migration
        e4_migration_res = run_stage4_event_sourcing_migration(db)
        if not e4_migration_res.success:
            raise RuntimeError(
                f"Startup halted: Stage 4 Event Sourcing migration failed: {e4_migration_res.error_message}"
            )
        # Verify CQRS projection integrity against event store
        verify_or_rebuild_at_startup(db)
    finally:
        db.close()

    # Start background scheduler for ACH settlement & recurring payments if enabled
    run_scheduler = os.getenv("RUN_SCHEDULER", "true").lower() == "true"
    if run_scheduler:
        start_background_scheduler(interval_seconds=10.0)
    try:
        yield
    finally:
        if run_scheduler:
            stop_background_scheduler()


app = FastAPI(
    title="Shift Bank API",
    description="Shift Bank Stage 4 Multicurrency REST API with Event Sourcing & CQRS.",
    version="4.0.0",
    lifespan=lifespan,
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(MfaRequiredException)
def mfa_required_exception_handler(request: Request, exc: MfaRequiredException):
    """Handle transfers and recurring schedules exceeding $1,000 without PIN by returning HTTP 428."""
    return JSONResponse(
        status_code=428,
        content={"detail": exc.detail, "message": exc.message},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Ensure consistent structured error responses for machine readability."""
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "ERROR")
        message = exc.detail.get("message", str(exc.detail))
        content = {
            "code": code,
            "message": message,
            "detail": exc.detail,
        }
        return JSONResponse(status_code=exc.status_code, content=content)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

# Register routers
app.include_router(accounts.router)
app.include_router(transfers.router)
app.include_router(conversions.router)
app.include_router(transactions.router)
app.include_router(beneficiaries.router)
app.include_router(limits.router)
app.include_router(recurring.router)
app.include_router(crypto.router)
app.include_router(audit.router)


@app.get("/api/health", tags=["Health"])
def health_check():
    """Service health check endpoint."""
    return {"status": "ok", "service": "shift-bank-api", "version": "4.0.0"}
