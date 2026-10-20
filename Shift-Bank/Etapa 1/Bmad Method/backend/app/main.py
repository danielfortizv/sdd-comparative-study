from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.database import get_connection, init_db
from .core.seed import seed_database

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

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def healthcheck():
    return {"status": "healthy", "stage": 1, "currency": "USD"}
