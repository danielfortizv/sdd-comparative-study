"""Real multi-process, real-broker E2E harness (Stage 4 R7.2, R7.3).

Boots the four services (identity, commerce, reviews, gateway) as independent
OS processes against the provisioned RabbitMQ broker, each with its own SQLite
store in a temp directory and a per-run event namespace so broker state does not
leak between runs. Drives the stack only through the gateway over HTTP.

Skips (rather than fails) the whole module if the broker is unreachable, so the
unit suites still run on machines without RabbitMQ; the broker is required for a
genuine acceptance run and its availability is asserted in CI.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import httpx
import pytest

try:
    import pika
except ImportError:  # pragma: no cover
    pika = None

ROOT = Path(__file__).resolve().parent.parent
SERVICES = ROOT / "services"
VENV_PYTHON = SERVICES / ".venv" / "Scripts" / "python.exe"
PYTHON = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

AMQP_URL = os.environ.get(
    "AMQP_URL", "amqp://ecommerce:stage4-demo@127.0.0.1:5672/stage4_kiro"
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _broker_available() -> bool:
    if pika is None:
        return False
    try:
        conn = pika.BlockingConnection(pika.URLParameters(AMQP_URL))
        conn.close()
        return True
    except Exception:  # noqa: BLE001
        return False


def _wait_health(port: int, timeout: float = 40.0) -> None:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/health"
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            resp = httpx.get(url, timeout=2.0)
            if resp.status_code == 200:
                return
        except Exception as error:  # noqa: BLE001
            last_error = error
        time.sleep(0.5)
    raise RuntimeError(f"service on port {port} not healthy: {last_error}")


class Stack:
    """A running Stage 4 stack addressed through the gateway."""

    def __init__(self, gateway_port: int, namespace: str, env: dict):
        self.gateway_port = gateway_port
        self.namespace = namespace
        self.env = env
        self.base = f"http://127.0.0.1:{gateway_port}"
        self.commerce_port = int(env["COMMERCE_PORT"])
        self.reviews_port = int(env["REVIEWS_PORT"])
        self.procs: dict[str, subprocess.Popen] = {}

    def client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base, timeout=10.0)


def _start(name: str, port: int, env: dict) -> subprocess.Popen:
    cwd = SERVICES / name
    return subprocess.Popen(
        [PYTHON, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(cwd),
        env=env,
    )


@pytest.fixture(scope="module")
def stack():
    if not _broker_available():
        pytest.skip(f"RabbitMQ broker not reachable at {AMQP_URL}")

    tmp = Path(tempfile.mkdtemp(prefix="stage4-e2e-"))
    namespace = f"stage4.kiro.e2e.{uuid.uuid4().hex[:8]}"
    ports = {
        "IDENTITY_PORT": _free_port(),
        "COMMERCE_PORT": _free_port(),
        "REVIEWS_PORT": _free_port(),
        "GATEWAY_PORT": _free_port(),
    }
    base_env = os.environ.copy()
    base_env.update(
        {
            "AMQP_URL": AMQP_URL,
            "EVENT_NAMESPACE": namespace,
            "IDENTITY_PORT": str(ports["IDENTITY_PORT"]),
            "COMMERCE_PORT": str(ports["COMMERCE_PORT"]),
            "REVIEWS_PORT": str(ports["REVIEWS_PORT"]),
            "GATEWAY_PORT": str(ports["GATEWAY_PORT"]),
            "IDENTITY_URL": f"http://127.0.0.1:{ports['IDENTITY_PORT']}",
            "COMMERCE_URL": f"http://127.0.0.1:{ports['COMMERCE_PORT']}",
            "REVIEWS_URL": f"http://127.0.0.1:{ports['REVIEWS_PORT']}",
            "IDENTITY_DB_PATH": str(tmp / "identity.db"),
            "COMMERCE_DB_PATH": str(tmp / "commerce.db"),
            "REVIEWS_DB_PATH": str(tmp / "reviews.db"),
            "REVIEW_IMAGE_DIR": str(tmp / "images"),
            "CATALOG_CACHE_TTL_SECONDS": "2",
            "STAGE4_TOKEN_SECRET": "e2e-secret",
        }
    )

    s = Stack(ports["GATEWAY_PORT"], namespace, base_env)
    # Start business services first, then the gateway.
    s.procs["identity"] = _start("identity", ports["IDENTITY_PORT"], base_env)
    s.procs["commerce"] = _start("commerce", ports["COMMERCE_PORT"], base_env)
    s.procs["reviews"] = _start("reviews", ports["REVIEWS_PORT"], base_env)
    try:
        _wait_health(ports["IDENTITY_PORT"])
        _wait_health(ports["COMMERCE_PORT"])
        _wait_health(ports["REVIEWS_PORT"])
        s.procs["gateway"] = _start("gateway", ports["GATEWAY_PORT"], base_env)
        _wait_health(ports["GATEWAY_PORT"])
        yield s
    finally:
        for proc in s.procs.values():
            proc.terminate()
        for proc in s.procs.values():
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


def restart_commerce(s: Stack) -> None:
    """Stop and restart only the commerce service (consumer) for outage tests."""
    proc = s.procs["commerce"]
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    s.procs["commerce"] = _start("commerce", s.commerce_port, s.env)
    _wait_health(s.commerce_port)
