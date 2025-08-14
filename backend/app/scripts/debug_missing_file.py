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
import asyncio

# Ensure 'app' package (backend/app) is importable when run from repo root.
# We insert backend/app's parent (backend) so imports like 'app.core.database' work.
_THIS = Path(__file__).resolve()
# Directory layout: backend/app/scripts/debug_missing_file.py
# parents[0]=scripts, [1]=app, [2]=backend, [3]=repo root
_BACKEND_DIR = _THIS.parents[2]  # backend directory containing the 'app' package
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

try:
    from app.core.database import engine  # type: ignore
    from app.models.tables import Receipt  # type: ignore
except ModuleNotFoundError as e:
    print("Import failure: ", e)
    print("sys.path=", sys.path)
    raise


async def _run_async(rid: int):
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        rec = (await session.execute(select(Receipt).where(Receipt.id == rid))).scalar_one_or_none()
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


def main():
    if len(sys.argv) < 2:
        print("Provide receipt_id")
        return
    rid = int(sys.argv[1])
    asyncio.run(_run_async(rid))

if __name__ == '__main__':
    main()
