"""Pytest configuration for the reviews service.

Makes the service root importable, points the review store and image folder at
temporary locations, and disables the background outbox relay so unit tests run
without a broker.
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

_tmp = Path(tempfile.gettempdir())
os.environ["REVIEWS_DB_PATH"] = str(_tmp / f"reviews-test-{uuid.uuid4().hex}.db")
os.environ["REVIEW_IMAGE_DIR"] = str(_tmp / f"reviews-img-{uuid.uuid4().hex}")
os.environ["REVIEWS_DISABLE_RELAY"] = "1"
