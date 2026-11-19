"""Aplicación FastAPI de Shift Bank (Etapa 1).

Registra los routers, habilita CORS para el frontend y ejecuta la siembra idempotente
del estado inicial en el arranque (Requisitos 9.1, 1.1).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .db import get_connection, init_schema, migrate, migrate_encryption
from .routers import accounts, ach, audit, beneficiaries, limits, recurring, transfers
from .scheduler import Scheduler
from .seed import seed, seed_limits


def _initialize_database() -> None:
    """Inicialización del arranque: esquema E1 → migración E2 → siembra → límites.

    Orden (Tarea 12): `init_schema` (E1) y `migrate` (E2) son idempotentes; `seed` (E1) y
    `seed_limits` (E2, Tarea 11) también. Reiniciar no duplica datos.
    """
    conn = get_connection()
    try:
        init_schema(conn)
        migrate(conn)              # Etapa 2 (Tarea 7/8): evolución aditiva, idempotente, transaccional.
        migrate_encryption(conn)   # Etapa 3 (Tarea 8): cifra en reposo registros heredados; idempotente/transaccional.
        seed(conn)                 # Etapa 1: cliente, cuentas, históricas (idempotente).
        seed_limits(conn)      # Etapa 2 (Tarea 11): límites por defecto (idempotente).
    finally:
        conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la app (Tarea 12/32): reemplaza `on_event("startup")` por `lifespan`.

    En el arranque inicializa la base de datos y lanza la **única** tarea asyncio del scheduler
    de fondo (Tarea 32, D02/D07): cada `SCHEDULER_TICK_SECONDS` ejecuta los recurrentes vencidos
    y el barrido de settlement ACH. En el apagado la cancela limpiamente (Req. 10.2). No se
    expone ningún endpoint administrativo para dispararlos (Req. 10.6). La recuperación tras
    reinicio es natural vía `next_run_at`/`schedule_execution` (no hay estado en memoria).

    Etapa 3 (Tarea 5, D-E3-01/02): ANTES de inicializar la base de datos o servir
    tráfico, se validan las claves externas requeridas (`SHIFT_ENC_KEYS`,
    `SHIFT_ENC_ACTIVE_KID`, `SHIFT_AUDIT_HMAC_KEY`). Si falta o es inválida alguna,
    `validate_startup_config` lanza `ConfigError` y el arranque ABORTA (fail-closed,
    R2.2/R12.2/R15.3): la excepción propaga fuera de `lifespan`, así el proceso no
    sirve peticiones. El material de clave nunca se registra (R2.6).
    """
    config.validate_startup_config()
    _initialize_database()
    scheduler = Scheduler()
    scheduler.start()
    app.state.scheduler = scheduler
    try:
        yield
    finally:
        await scheduler.stop()


app = FastAPI(title="Shift Bank", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts.router)
app.include_router(transfers.router)
app.include_router(limits.router)
app.include_router(beneficiaries.router)
app.include_router(ach.router)
app.include_router(recurring.router)
# Etapa 3 (Tarea 15): verificación de auditoría protegida por SHIFT_ADMIN_TOKEN (§2.5/§2.6).
app.include_router(audit.router)
