"""Storage service abstraction.

Supports two backends selected via ``settings.STORAGE_BACKEND``:

1. **minio** (default): Uses the MinIO S3‑compatible object storage.
2. **filesystem**: Stores files under ``settings.STORAGE_DIRECTORY`` on disk.

All saved objects return a *relative key* (``user_id/uuid_filename``) that
is persisted on the receipt row. Retrieval resolves the key according to
the active backend. For MinIO we stream directly from the bucket; for the
filesystem we read from disk. A legacy filesystem fallback is kept for
older stored paths.
"""

import uuid
from pathlib import Path
from typing import Tuple
from io import BytesIO

from fastapi import UploadFile

from app.core.config import settings

try:  # Optional dependency (listed in requirements)
    from minio import Minio  # type: ignore
    from minio.error import S3Error  # type: ignore
except Exception:  # pragma: no cover - MinIO not installed
    Minio = None  # type: ignore
    S3Error = Exception  # type: ignore


class StorageService:
    """Unified storage service (MinIO or filesystem)."""

    def __init__(self, base_dir: str | None = None) -> None:
        self.backend = (settings.STORAGE_BACKEND or "minio").lower()
        if self.backend == "minio" and Minio is not None:
            self._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=bool(settings.MINIO_USE_SSL),
            )
            self.bucket = settings.MINIO_BUCKET_NAME
            # Ensure bucket exists (idempotent)
            try:
                if not self._client.bucket_exists(self.bucket):  # type: ignore[attr-defined]
                    self._client.make_bucket(self.bucket)  # type: ignore[attr-defined]
            except Exception as e:  # pragma: no cover - startup path
                print(f"[storage] MinIO bucket ensure failed: {e}")
        else:
            # Fallback to filesystem
            self.backend = "filesystem"
            base_dir_str = base_dir or settings.STORAGE_DIRECTORY
            base_path = Path(base_dir_str)
            if not base_path.is_absolute():
                repo_root = Path(__file__).resolve().parents[3]
                base_path = (repo_root / base_path).resolve()
            self.base_dir = base_path
            self.base_dir.mkdir(parents=True, exist_ok=True)
            print(f"[storage] Filesystem base_dir: {self.base_dir}")

    def _normalise_filename(self, filename: str) -> str:
        """Remove potentially dangerous characters and ensure a safe filename."""
        keepchars = {"-", "_", "."}
        return "".join(c for c in filename if c.isalnum() or c in keepchars)

    async def save_upload(self, upload: UploadFile, user_id: int) -> Tuple[str, str]:
        """Persist an uploaded file (to MinIO or filesystem) and return (key, original_name)."""
        original_name = upload.filename or "receipt"
        safe_name = self._normalise_filename(original_name)
        unique_id = uuid.uuid4().hex
        object_name = f"{user_id}/{unique_id}_{safe_name}"  # user namespace

        if hasattr(upload.file, "seek"):
            try:
                upload.file.seek(0)
            except Exception:
                pass

        contents = await upload.read()
        if not contents:
            raise RuntimeError("Empty upload payload")

        if self.backend == "minio":
            try:
                # Upload from memory buffer
                data_stream = BytesIO(contents)
                length = len(contents)
                self._client.put_object(  # type: ignore[attr-defined]
                    self.bucket,
                    object_name,
                    data_stream,
                    length,
                    content_type=upload.content_type or "application/octet-stream",
                )
                print(f"[storage] MinIO object put: {object_name} size={length}")
            except Exception as e:
                raise RuntimeError(f"MinIO upload failed: {e}")
            return object_name, original_name

        # Filesystem path
        user_dir = self.base_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        file_path = user_dir / object_name.split("/", 1)[1]  # strip user_id/ prefix for directory duplication
        file_path.write_bytes(contents)
        try:
            size = file_path.stat().st_size
        except Exception:
            size = -1
        print(f"[storage] FS saved: {file_path} bytes={size}")
        if size <= 0:
            raise RuntimeError(f"Wrote zero bytes to {file_path}; upload may be empty")
        relative_key = f"{user_id}/{file_path.name}"
        return relative_key, original_name

        def get_full_path(self, relative_path: str) -> Path:
            """Resolve a stored file's full path (filesystem only)."""
            return self.base_dir / relative_path


# Standalone function for use by background tasks
def load_file_from_storage(file_key: str) -> bytes:
    """Load raw bytes for a stored file / object by key.

    For MinIO the key is the object name. For filesystem it is the
    relative path (user_id/filename). Includes a legacy fallback.
    """
    storage = StorageService()
    print(f"[storage] load request key={file_key} backend={storage.backend}")

    if storage.backend == "minio":  # Use object store
        try:
            resp = storage._client.get_object(storage.bucket, file_key)  # type: ignore[attr-defined]
            try:
                data = resp.read()  # read whole object (small images ok)
                print(f"[storage] MinIO get ok key={file_key} bytes={len(data)}")
                return data
            finally:
                resp.close()
                resp.release_conn()
        except S3Error as e:  # pragma: no cover - network path
            raise ValueError(f"File not found: {file_key}") from e
        except Exception as e:  # Other errors
            raise RuntimeError(f"MinIO download failed: {e}")

    # Filesystem path
    full_path = storage.get_full_path(file_key)
    print(f"[storage] FS lookup {full_path}")
    try:
        return full_path.read_bytes()
    except FileNotFoundError:
        repo_root = Path(__file__).resolve().parents[3]
        legacy_path = (repo_root / "backend" / "storage" / file_key).resolve()
        print(f"[storage] Legacy FS check {legacy_path}")
        if legacy_path.exists():
            return legacy_path.read_bytes()
        raise ValueError(f"File not found: {file_key}")