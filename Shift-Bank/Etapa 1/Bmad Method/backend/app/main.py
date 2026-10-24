from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .core.database import get_connection, init_db
from .core.seed import seed_database
from .api.accounts import router as accounts_router
from .api.transfers import router as transfers_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema and seed initial portfolio
    conn = get_connection()
    try:
        init_db(conn)
        seed_database(conn)
    finally:
        conn.close()
    yield

app = FastAPI(
    title="Shift Bank API",
    version="1.0.0",
    description="Shift Bank Stage 1 core banking retail API",
    lifespan=lifespan,
)

# Standardized Error Envelope Handler (AD-10)
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        if "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        if "code" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "HTTP_ERROR", "message": str(exc.detail)}},
    )

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(accounts_router, prefix="/api")
app.include_router(transfers_router, prefix="/api")

@app.get("/api/health")
def healthcheck():
    return {"status": "healthy", "stage": 1, "currency": "USD"}
