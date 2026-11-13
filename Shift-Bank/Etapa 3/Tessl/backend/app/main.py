from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
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
)
from backend.app.services.account_service import seed_initial_data
from backend.app.services.transfer_service import MfaRequiredException
from backend.app.services.scheduler import start_background_scheduler, stop_background_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and seed data
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()

    # Start background scheduler for ACH settlement & recurring payments
    start_background_scheduler(interval_seconds=10.0)
    try:
        yield
    finally:
        stop_background_scheduler()


app = FastAPI(
    title="Shift Bank API",
    description="Shift Bank Stage 2 REST API for mock user accounts, internal & ACH transfers, recurring payments, and dynamic limits.",
    version="2.0.0",
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

# Register routers
app.include_router(accounts.router)
app.include_router(transfers.router)
app.include_router(transactions.router)
app.include_router(beneficiaries.router)
app.include_router(limits.router)
app.include_router(recurring.router)


@app.get("/api/health", tags=["Health"])
def health_check():
    """Service health check endpoint."""
    return {"status": "ok", "service": "shift-bank-api", "version": "2.0.0"}
