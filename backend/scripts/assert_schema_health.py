"""Schema health assertions.

Run inside container:
  docker compose run --rm api python scripts/assert_schema_health.py

Checks:
  1. Single Alembic head
  2. Presence of composite index ix_receipts_owner_created_at
"""
from __future__ import annotations

import subprocess
import os
from sqlalchemy import create_engine, text


def assert_single_head() -> None:
    result = subprocess.run(["alembic", "heads"], capture_output=True, text=True, check=True)
    lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
    if len(lines) != 1:
        raise SystemExit(f"Expected 1 alembic head, found {len(lines)}: {lines}")
    print(f"[ok] single alembic head: {lines[0]}")


def assert_receipts_index() -> None:
    url = os.environ.get("ALEMBIC_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL / ALEMBIC_DATABASE_URL not set")
    url = url.replace("+asyncpg", "+psycopg")
    engine = create_engine(url, pool_pre_ping=True)
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT indexname FROM pg_indexes WHERE schemaname='public' AND tablename='receipts'" )).fetchall()
        names = {r[0] for r in rows}
        if "ix_receipts_owner_created_at" not in names:
            raise SystemExit("Missing index ix_receipts_owner_created_at")
        print("[ok] composite index present on receipts")


def main() -> int:
    assert_single_head()
    assert_receipts_index()
    print("Schema health OK.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
