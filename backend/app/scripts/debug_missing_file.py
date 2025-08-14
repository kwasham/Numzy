"""Utility script to inspect a receipt's stored file path.

Usage (from repo root):

python -m backend.app.scripts.debug_missing_file <receipt_id>

Prints:
- DB record path
- Resolved full path
- Existence + size
- Legacy fallback path
"""
from pathlib import Path
import sys
from sqlalchemy import select

# Ensure 'app' package (backend/app) is importable when run from repo root.
# We insert backend/app's parent (backend) so imports like 'app.core.database' work.
_THIS = Path(__file__).resolve()
_BACKEND_DIR = _THIS.parents[3]  # .../backend
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.database import engine  # type: ignore
from app.models.tables import Receipt  # type: ignore


def main():
    if len(sys.argv) < 2:
        print("Provide receipt_id")
        return
    rid = int(sys.argv[1])
    # Use a synchronous session bound to the same engine (engine may be async creator)
    from sqlalchemy.orm import sessionmaker
    sync_engine = engine.sync_engine if hasattr(engine, 'sync_engine') else engine
    SessionLocal = sessionmaker(bind=sync_engine)
    with SessionLocal() as session:
        rec = session.execute(select(Receipt).where(Receipt.id == rid)).scalar_one_or_none()
        if not rec:
            print(f"Receipt {rid} not found")
            return
        rel = rec.file_path
        print(f"DB file_path: {rel}")
        from app.services.storage_service import StorageService
        storage = StorageService()
        full = storage.get_full_path(rel)
        print(f"Resolved full path: {full}")
        print(f"Exists: {full.exists()} Size: {full.stat().st_size if full.exists() else 'n/a'}")
        repo_root = Path(__file__).resolve().parents[4]
        legacy = (repo_root / 'backend' / 'storage' / rel).resolve()
        print(f"Legacy path: {legacy} Exists: {legacy.exists()}")

if __name__ == '__main__':
    main()
