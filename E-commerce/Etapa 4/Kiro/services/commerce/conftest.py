"""Pytest configuration for the commerce service.

Makes the service root importable, points the projection store at a temporary
SQLite file, and disables the live broker consumer so unit tests exercise HTTP
and projection logic without a running RabbitMQ.
"""

from __future__ import annotations

import os
import sys
import tempfile
import uuid
from pathlib import Path

_SERVICE_ROOT = Path(__file__).resolve().parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))

os.environ["COMMERCE_DB_PATH"] = str(
    Path(tempfile.gettempdir()) / f"commerce-test-{uuid.uuid4().hex}.db"
)
os.environ["COMMERCE_DISABLE_CONSUMER"] = "1"
