"""Storage service abstraction.

This service encapsulates all interactions with the underlying
storage layer. In a local development environment files are saved
to the filesystem under the directory specified by
``settings.STORAGE_DIRECTORY``. In production you can replace
this implementation with a wrapper around an S3 compatible API
such as MinIO or AWS S3.

The methods provided by this class should be side‑effect free
where possible. All file names are normalised to avoid path
traversal issues and collisions. You can extend this service to
generate presigned URLs or integrate thumbnail generation.
"""

import os
import uuid
from pathlib import Path
from typing import Tuple

from fastapi import UploadFile

from app.core.config import settings


class StorageService:
    """File storage service supporting local filesystem storage."""

    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = Path(base_dir or settings.STORAGE_DIRECTORY)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _normalise_filename(self, filename: str) -> str:
        """Remove potentially dangerous characters and ensure a safe filename."""
        keepchars = {"-", "_", "."}
        return "".join(c for c in filename if c.isalnum() or c in keepchars)

    async def save_upload(self, upload: UploadFile, user_id: int) -> Tuple[str, str]:
        """Persist an uploaded file to storage and return its path and filename.

        :param upload: The uploaded file object from FastAPI
        :param user_id: ID of the user who owns the file
        :returns: A tuple of (file_path, filename) relative to the storage root
        """
        # Normalise filename to avoid directory traversal
        original_name = upload.filename or "receipt"
        safe_name = self._normalise_filename(original_name)

        # Generate a unique identifier to avoid collisions
        unique_id = uuid.uuid4().hex
        filename = f"{unique_id}_{safe_name}"

        # Determine the user's directory
        user_dir = self.base_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        file_path = user_dir / filename
        # Write the file asynchronously
        contents = await upload.read()
        file_path.write_bytes(contents)

        # Return relative path for storing in DB and the actual filename
        relative_path = str(file_path.relative_to(self.base_dir))
        return relative_path, original_name

    def get_full_path(self, relative_path: str) -> Path:
        """Resolve a stored file's full path on the filesystem."""
        return self.base_dir / relative_path