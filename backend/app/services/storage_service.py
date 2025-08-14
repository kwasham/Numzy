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

import uuid
from pathlib import Path
from typing import Tuple

from fastapi import UploadFile

from app.core.config import settings


class StorageService:
    """File storage service supporting local filesystem storage."""

    def __init__(self, base_dir: str | None = None) -> None:
        # Resolve base directory to an absolute path rooted at the repo
        base_dir_str = base_dir or settings.STORAGE_DIRECTORY
        base_path = Path(base_dir_str)
        if not base_path.is_absolute():
            # backend/app/services -> repo root is parents[3]
            repo_root = Path(__file__).resolve().parents[3]
            base_path = (repo_root / base_path).resolve()
        self.base_dir = base_path
        self.base_dir.mkdir(parents=True, exist_ok=True)
        # Debug: show resolved base dir
        print(f"Storage base_dir resolved to: {self.base_dir}")

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
        
        # Check if file content is already read
        if hasattr(upload.file, 'seek'):
            upload.file.seek(0)
        
        # Write the file asynchronously
        contents = await upload.read()
        file_path.write_bytes(contents)
        # Debug: confirm write and size
        try:
            size = file_path.stat().st_size
        except Exception:
            size = -1
        print(f"Saved file to: {file_path} (bytes={len(contents)}, on_disk={size})")
        if size <= 0:
            raise RuntimeError(f"Wrote zero bytes to {file_path}; upload may be empty")

        # Return relative path for storing in DB and the actual filename
        relative_path = str(file_path.relative_to(self.base_dir))
        return relative_path, original_name

    def get_full_path(self, relative_path: str) -> Path:
        """Resolve a stored file's full path on the filesystem."""
        return self.base_dir / relative_path


# Standalone function for use by background tasks
def load_file_from_storage(file_path: str) -> bytes:
    """Load a file from storage.

    Args:
        file_path: The relative path to the file in storage

    Returns:
        The file contents as bytes
    """
    # Create a storage service instance
    storage = StorageService()

    # Get the full path
    full_path = storage.get_full_path(file_path)
    print(f"Looking for file at: {file_path}")
    print(f"Looking for file at: {full_path}")

    # Read and return the file
    try:
        with open(full_path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        # Fallback: check legacy backend/storage location
        repo_root = Path(__file__).resolve().parents[3]
        legacy_path = (repo_root / "backend" / "storage" / file_path).resolve()
        print(f"Fallback check at: {legacy_path}")
        if legacy_path.exists():
            return legacy_path.read_bytes()
        raise ValueError(f"File not found: {file_path}")