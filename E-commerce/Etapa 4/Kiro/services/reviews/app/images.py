"""On-disk review image store owned by the reviews service (Stage 3 parity).

Validates and persists review image bytes in a local folder. The same
allow-list (JPEG/PNG/GIF/WebP), the 2 MB cap, and the up-to-three-per-review
rule as Stage 2/3 are preserved. Image bytes are the only on-disk artifact;
everything else lives in SQLite.
"""

from __future__ import annotations

import base64
import binascii
import os
import uuid
from pathlib import Path

ALLOWED_MEDIA_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
MAX_IMAGE_BYTES = 2 * 1024 * 1024

_DEFAULT_DIR = Path(__file__).resolve().parent.parent / "review_images"


def _image_dir() -> Path:
    return Path(os.environ.get("REVIEW_IMAGE_DIR", str(_DEFAULT_DIR)))


class ImageValidationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ImageStore:
    def __init__(self, image_dir: Path | None = None) -> None:
        self._image_dir = image_dir if image_dir is not None else _image_dir()
        self._image_dir.mkdir(parents=True, exist_ok=True)

    def validate(self, media_type: str, data_base64: str) -> bytes:
        if media_type not in ALLOWED_MEDIA_TYPES:
            raise ImageValidationError(
                "unsupported_image_type",
                "Unsupported image type. Allowed types are JPEG, PNG, GIF, and WebP.",
            )
        try:
            raw = base64.b64decode(data_base64, validate=True)
        except (binascii.Error, ValueError):
            raise ImageValidationError(
                "invalid_image_data", "An attached image could not be read."
            )
        if len(raw) == 0:
            raise ImageValidationError(
                "invalid_image_data", "An attached image is empty."
            )
        if len(raw) > MAX_IMAGE_BYTES:
            raise ImageValidationError(
                "image_too_large", "An attached image exceeds the 2 MB size limit."
            )
        return raw

    def store(self, media_type: str, data_base64: str) -> tuple[str, str]:
        raw = self.validate(media_type, data_base64)
        image_id = str(uuid.uuid4())
        filename = f"{image_id}{ALLOWED_MEDIA_TYPES[media_type]}"
        self._image_dir.mkdir(parents=True, exist_ok=True)
        (self._image_dir / filename).write_bytes(raw)
        return image_id, filename

    def read(self, filename: str) -> tuple[bytes, str]:
        path = self._image_dir / filename
        if not path.is_file():
            raise FileNotFoundError(filename)
        return path.read_bytes(), _media_type_from_filename(filename)

    def clear(self) -> None:
        if self._image_dir.exists():
            for child in self._image_dir.iterdir():
                if child.is_file() and child.name != ".gitignore":
                    child.unlink()


def _media_type_from_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    for media_type, extension in ALLOWED_MEDIA_TYPES.items():
        if extension == suffix:
            return media_type
    return "application/octet-stream"
