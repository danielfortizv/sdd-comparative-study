"""Local on-disk review image storage (data-access layer, Stage 2).

Review image bytes are the single on-disk artifact in Stage 2 (Assumption A3,
A6). This module validates submitted images (media-type allow-list and size
cap), writes accepted bytes to a local, git-ignored demonstration folder, and
reads them back for serving through the image endpoint. No external object
storage, CDN, or paid service is used (Requirement 2.7).

Images arrive base64-encoded with a declared media type. A rejected
attachment is never written to disk (Requirements 2.3, 2.4, 6.3).
"""

from __future__ import annotations

import base64
import binascii
import uuid
from pathlib import Path

# Allowed image media types (Assumption A3). Anything else is rejected.
ALLOWED_MEDIA_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}

# Maximum accepted size for a single decoded image: 2 MB (Assumption A3).
MAX_IMAGE_BYTES = 2 * 1024 * 1024

# Local demonstration folder for stored image bytes. Resolved relative to this
# file so it works regardless of the process working directory.
IMAGE_DIR = Path(__file__).resolve().parent / "review_images"


class ImageValidationError(Exception):
    """Raised when a submitted image fails validation.

    Carries a stable ``code`` and a safe, human-readable ``message`` so the
    service and API layers can surface a structured error without exposing
    internal detail (Requirement 6.1).
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ImageStore:
    """Validates and stores review image bytes in a local folder."""

    def __init__(self, image_dir: Path | None = None) -> None:
        self._image_dir = image_dir if image_dir is not None else IMAGE_DIR
        self._media_types: dict[str, str] = {}
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        self._image_dir.mkdir(parents=True, exist_ok=True)

    def validate(self, media_type: str, data_base64: str) -> bytes:
        """Validate a single image and return its decoded bytes.

        Does not write anything; a caller that wants to persist must call
        :meth:`store`. Raises :class:`ImageValidationError` for an unsupported
        media type, undecodable data, or an oversized image (Requirements 2.3,
        2.4, 6.3).
        """
        if media_type not in ALLOWED_MEDIA_TYPES:
            raise ImageValidationError(
                code="unsupported_image_type",
                message=(
                    "Unsupported image type. Allowed types are JPEG, PNG, "
                    "GIF, and WebP."
                ),
            )
        try:
            raw = base64.b64decode(data_base64, validate=True)
        except (binascii.Error, ValueError):
            raise ImageValidationError(
                code="invalid_image_data",
                message="An attached image could not be read.",
            )
        if len(raw) == 0:
            raise ImageValidationError(
                code="invalid_image_data",
                message="An attached image is empty.",
            )
        if len(raw) > MAX_IMAGE_BYTES:
            raise ImageValidationError(
                code="image_too_large",
                message="An attached image exceeds the 2 MB size limit.",
            )
        return raw

    def store(self, media_type: str, data_base64: str) -> tuple[str, str]:
        """Validate and persist a single image.

        Returns ``(image_id, filename)``. Only called after validation passes,
        so a rejected attachment is never written (Requirements 2.5, 6.3).
        """
        raw = self.validate(media_type, data_base64)
        image_id = str(uuid.uuid4())
        extension = ALLOWED_MEDIA_TYPES[media_type]
        filename = f"{image_id}{extension}"
        self._ensure_dir()
        (self._image_dir / filename).write_bytes(raw)
        self._media_types[image_id] = media_type
        return image_id, filename

    def read(self, image_id: str, filename: str) -> tuple[bytes, str]:
        """Return ``(bytes, media_type)`` for a stored image.

        Raises:
            FileNotFoundError: If the image is not present on disk.
        """
        path = self._image_dir / filename
        if not path.is_file():
            raise FileNotFoundError(image_id)
        media_type = self._media_types.get(image_id)
        if media_type is None:
            # Recover the media type from the extension if the in-memory map
            # was reset (for example after a process restart in the demo).
            media_type = _media_type_from_filename(filename)
        return path.read_bytes(), media_type

    def clear(self) -> None:
        """Remove all stored image files and metadata. Provided for tests."""
        if self._image_dir.exists():
            for child in self._image_dir.iterdir():
                if child.is_file() and child.name != ".gitignore":
                    child.unlink()
        self._media_types.clear()


def _media_type_from_filename(filename: str) -> str:
    """Best-effort media type from a stored filename's extension."""
    suffix = Path(filename).suffix.lower()
    for media_type, extension in ALLOWED_MEDIA_TYPES.items():
        if extension == suffix:
            return media_type
    return "application/octet-stream"


# Shared local image store for the running service.
image_store = ImageStore()
