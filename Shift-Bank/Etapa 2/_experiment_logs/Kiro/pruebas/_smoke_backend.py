"""Smoke test de verificacion de la app heredada (Etapa 2, Kiro).

NO forma parte de la aplicacion: es evidencia de verificacion de la copia.
Ejercita el ciclo de arranque (schema + seed idempotente) y los endpoints principales
contra una base de datos SQLite TEMPORAL y AISLADA. Nunca toca shift_bank.db.

No requiere dependencias fuera de requirements.txt: invoca la app ASGI directamente
mediante asyncio, sin httpx ni TestClient.

Uso:
    python _smoke_backend.py <ruta_backend_copia>
"""

import asyncio
import json
import sys
import tempfile
import pathlib

backend_root = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(backend_root))

# DB temporal aislada: se parchea ANTES de importar la app.
tmp_db = pathlib.Path(tempfile.gettempdir()) / "e2_kiro_smoke.db"
if tmp_db.exists():
    tmp_db.unlink()

import app.config as config  # noqa: E402

config.DB_PATH = tmp_db
import app.db as db  # noqa: E402

db.DB_PATH = tmp_db

from app.main import app  # noqa: E402

failures = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name} {detail}")
    if not cond:
        failures.append(name)


async def lifespan_startup(app):
    """Dispara los handlers de startup (schema + seed) via protocolo ASGI."""
    events = iter([{"type": "lifespan.startup"}])

    async def receive():
        try:
            return next(events)
        except StopIteration:
            # Mantener vivo el scope hasta shutdown.
            await asyncio.sleep(3600)

    sent = []

    async def send(msg):
        sent.append(msg)

    task = asyncio.ensure_future(
        app({"type": "lifespan", "asgi": {"version": "3.0"}}, receive, send)
    )
    # Esperar a que complete el startup.
    for _ in range(100):
        await asyncio.sleep(0.01)
        if any(m["type"] == "lifespan.startup.complete" for m in sent):
            break
    return task


async def call(app, method, path, body=None):
    """Invoca un endpoint HTTP via protocolo ASGI y devuelve (status, json)."""
    raw = json.dumps(body).encode() if body is not None else b""
    headers = [(b"host", b"testserver")]
    if body is not None:
        headers.append((b"content-type", b"application/json"))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers,
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 12345),
    }

    body_sent = False

    async def receive():
        nonlocal body_sent
        if not body_sent:
            body_sent = True
            return {"type": "http.request", "body": raw, "more_body": False}
        return {"type": "http.disconnect"}

    status_holder = {}
    chunks = []

    async def send(msg):
        if msg["type"] == "http.response.start":
            status_holder["status"] = msg["status"]
        elif msg["type"] == "http.response.body":
            chunks.append(msg.get("body", b""))

    await app(scope, receive, send)
    payload = b"".join(chunks)
    parsed = json.loads(payload) if payload else None
    return status_holder.get("status"), parsed


async def main():
    await lifespan_startup(app)

    check("DB temporal creada", tmp_db.exists(), f"({tmp_db})")

    status, data = await call(app, "GET", "/api/accounts")
    check("GET /api/accounts 200", status == 200, f"-> {status}")
    accounts = (data or {}).get("accounts", [])
    check("Dos cuentas sembradas", len(accounts) == 2, f"-> {len(accounts)}")
    names = sorted(a["name"] for a in accounts)
    check("Cuentas Checking/Savings", names == ["Checking", "Savings"], f"-> {names}")

    status, data = await call(app, "GET", "/api/transfers")
    check("GET /api/transfers 200", status == 200, f"-> {status}")
    hist = (data or {}).get("transfers", [])
    check("Dos transferencias historicas", len(hist) == 2, f"-> {len(hist)}")

    status, body = await call(
        app, "POST", "/api/transfers",
        {"from": "checking", "to": "savings", "amount": "1000.00",
         "description": "smoke test"},
    )
    check("POST /api/transfers 201", status == 201, f"-> {status}")
    check("Transferencia sin MFA requerida", (body or {}).get("mfa_required") is False,
          f"-> {(body or {}).get('mfa_required')}")

    # Historial tras la transferencia: 2 historicas + 1 nueva = 3.
    status, data = await call(app, "GET", "/api/transfers")
    hist2 = (data or {}).get("transfers", [])
    check("Historial refleja nueva transferencia", len(hist2) == 3, f"-> {len(hist2)}")


asyncio.run(main())

if tmp_db.exists():
    tmp_db.unlink()

print(f"\nRESULTADO: {'OK - todos los checks pasaron' if not failures else 'FALLOS: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
