from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.app.database import engine, Base, SessionLocal
from backend.app.routers import accounts, transfers, transactions
from backend.app.services.account_service import seed_initial_data
from backend.app.services.transfer_service import MfaRequiredException


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and seed data
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Shift Bank API",
    description="Shift Bank Stage 1 REST API for authenticated mock user accounts, transfers, and transactions.",
    version="1.0.0",
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
    """Handle transfers exceeding $1,000 without PIN by returning HTTP 428."""
    return JSONResponse(
        status_code=428,
        content={"detail": exc.detail, "message": exc.message},
    )

# Register routers
app.include_router(accounts.router)
app.include_router(transfers.router)
app.include_router(transactions.router)


@app.get("/api/health", tags=["Health"])
def health_check():
    """Service health check endpoint."""
    return {"status": "ok", "service": "shift-bank-api", "version": "1.0.0"}
