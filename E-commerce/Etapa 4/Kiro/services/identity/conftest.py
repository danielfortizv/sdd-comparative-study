"""Pytest configuration for the identity service.

Ensures the service root (containing the ``app`` package) is importable and
points the account store at a temporary SQLite file so tests never touch the
real ``identity.db``.
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

# Each test session gets its own throwaway database file.
_tmp_db = Path(tempfile.gettempdir()) / f"identity-test-{uuid.uuid4().hex}.db"
os.environ["IDENTITY_DB_PATH"] = str(_tmp_db)
