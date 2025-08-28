"""Utility: Widen alembic_version.version_num length.

Run inside the API container:
  docker compose run --rm api python backend/scripts/alembic_widen_version_column.py

Safe to run multiple times. If the alembic_version table is missing we abort
so normal `alembic upgrade head` flow can create it instead of a manual table.
"""
from __future__ import annotations

from sqlalchemy import create_engine, text
import os
import sys

DEFAULT_URL = (
    "postgresql+psycopg://"
    "neondb_owner:npg_E9toQgW4aulJ@ep-proud-shape-adknsbkg-pooler.c-2.us-east-1.aws.neon.tech/"
    "receipts?sslmode=require&channel_binding=disable"
)


def main() -> int:
    url = os.environ.get("ALEMBIC_DATABASE_URL") or DEFAULT_URL
    # normalize async driver if present
    url = url.replace("+asyncpg", "+psycopg")
    print(f"[alembic_widen] Using DB: {url.split('@')[0]}@<redacted>")
    engine = create_engine(url, pool_pre_ping=True)
    with engine.begin() as conn:
        present = conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name='alembic_version'"
            )
        ).fetchone()
        if not present:
            print(
                "[alembic_widen] alembic_version table missing. Run regular migrations instead; no change made."
            )
            return 2
        row = conn.execute(
            text(
                "SELECT character_maximum_length FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='alembic_version' AND column_name='version_num'"
            )
        ).fetchone()
        current_len = row[0]
        print(f"[alembic_widen] Current length: {current_len}")
        if current_len is not None and current_len < 100:
            print("[alembic_widen] Altering version_num to VARCHAR(255)...")
            conn.execute(
                text(
                    "ALTER TABLE public.alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)"
                )
            )
            new_len = conn.execute(
                text(
                    "SELECT character_maximum_length FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='alembic_version' AND column_name='version_num'"
                )
            ).scalar()
            print(f"[alembic_widen] New length: {new_len}")
        else:
            print("[alembic_widen] No alteration needed.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
