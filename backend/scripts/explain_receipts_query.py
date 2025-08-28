"""Run EXPLAIN (ANALYZE, BUFFERS) on the hot receipts listing query.

Usage:
  docker compose run --rm api python scripts/explain_receipts_query.py [OWNER_ID] [LIMIT]

If OWNER_ID not supplied, picks a recent owner from receipts. LIMIT defaults to 50.
Outputs timing and whether the composite index is used.
"""
from __future__ import annotations

import os
import sys
from sqlalchemy import create_engine, text

def main() -> int:
    url = os.environ.get("ALEMBIC_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL / ALEMBIC_DATABASE_URL required", file=sys.stderr)
        return 2
    url = url.replace("+asyncpg", "+psycopg")
    engine = create_engine(url, pool_pre_ping=True)
    owner_id = None
    limit = 50
    if len(sys.argv) > 1:
        owner_id = sys.argv[1]
    if len(sys.argv) > 2:
        limit = int(sys.argv[2])
    with engine.begin() as conn:
        if owner_id is None:
            row = conn.execute(text("SELECT owner_id FROM receipts ORDER BY created_at DESC LIMIT 1")).fetchone()
            if not row:
                print("No receipts present; cannot run explain.")
                return 0
            owner_id = row[0]
        print(f"Using owner_id={owner_id} limit={limit}")
        sql = text("""
            EXPLAIN (ANALYZE, BUFFERS, COSTS, VERBOSE, SUMMARY)
            SELECT id, owner_id, created_at, status
            FROM receipts
            WHERE owner_id = :owner_id
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        plan_rows = conn.execute(sql, {"owner_id": owner_id, "limit": limit}).fetchall()
        print("--- QUERY PLAN ---")
        for (line,) in plan_rows:
            print(line)
        if not any('Index Scan' in line for (line,) in plan_rows):
            print("NOTE: Planner chose Seq Scan (table likely small or low selectivity). As data grows, the composite index should appear as an Index Scan or Index Only Scan.")
    return 0

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
