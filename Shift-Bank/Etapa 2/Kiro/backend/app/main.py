"""Aplicación FastAPI de Shift Bank (Etapa 1).

Registra los routers, habilita CORS para el frontend y ejecuta la siembra idempotente
del estado inicial en el arranque (Requisitos 9.1, 1.1).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import get_connection, init_schema
from .routers import accounts, transfers
from .seed import seed

app = FastAPI(title="Shift Bank", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts.router)
app.include_router(transfers.router)


@app.on_event("startup")
def _startup() -> None:
    conn = get_connection()
    try:
        init_schema(conn)
        seed(conn)
    finally:
        conn.close()
