"""Load test: find index crossover point for receipts owner query.

Generates batched synthetic receipts for a single test owner and times
the hot query after each batch, recording whether the planner uses the
composite index or a sequential scan.

Safeguards:
  - Requires env var ALLOW_DEV_LOADTEST=1 to run.
  - Aborts if run against a database name that looks like production.

Usage:
  docker compose run --rm -e ALLOW_DEV_LOADTEST=1 api \
      python scripts/loadtest_receipts_crossover.py [owner_id] [batches]

Example:
  docker compose run --rm -e ALLOW_DEV_LOADTEST=1 api \
      python scripts/loadtest_receipts_crossover.py 9999 5
"""
from __future__ import annotations

import os
import sys
import time
from typing import List, Dict, Any
from random import randint
from datetime import datetime, timezone
from sqlalchemy import create_engine, text

BATCH_SIZE = 500  # receipts inserted per batch
QUERY_LIMIT = 100


def guard() -> None:
    if os.environ.get("ALLOW_DEV_LOADTEST") != "1":
        print("Refusing to run. Set ALLOW_DEV_LOADTEST=1 to proceed.", file=sys.stderr)
        sys.exit(2)


def connect_url() -> str:
    url = os.environ.get("ALEMBIC_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL / ALEMBIC_DATABASE_URL required", file=sys.stderr)
        sys.exit(2)
    return url.replace("+asyncpg", "+psycopg")


def ensure_not_prod(conn) -> None:
    db = conn.execute(text("SELECT current_database()" )).scalar() or ""
    if any(token in db.lower() for token in ("prod", "production", "live")):
        print(f"Database '{db}' looks like production; aborting.", file=sys.stderr)
        sys.exit(3)


def insert_batch(conn, owner_id: int, batch: int) -> None:
    # Minimal columns to satisfy schema; rely on defaults for others.
    # We'll insert synthetic created_at descending-ish.
    rows = []
    for i in range(BATCH_SIZE):
        # spread created_at by random seconds
        rows.append({"owner_id": owner_id, "status": "completed"})
    # Use executemany with text insert; adjust columns as needed.
    conn.execute(
        text("INSERT INTO receipts (owner_id, status, created_at) VALUES (:owner_id, :status, NOW() - (random()* interval '10 days'))"),
        rows,
    )


def measure_plan(conn, owner_id: int) -> Dict[str, Any]:
    plan_rows = conn.execute(
        text(
            """
            EXPLAIN (ANALYZE, BUFFERS, COSTS, SUMMARY)
            SELECT id, owner_id, created_at, status
            FROM receipts
            WHERE owner_id=:o
            ORDER BY created_at DESC
            LIMIT :lim
            """
        ), {"o": owner_id, "lim": QUERY_LIMIT}
    ).fetchall()
    lines = [r[0] for r in plan_rows]
    used_index = any("Index Scan" in l or "Index Only Scan" in l for l in lines)
    actual_time_line = next((l for l in lines if "Execution Time" in l), "")
    return {
        "used_index": used_index,
        "plan": lines,
        "execution_time_ms": float(actual_time_line.split("Execution Time:")[-1].split(" ms")[0].strip()) if "Execution Time:" in actual_time_line else None,
    }


def main() -> int:
    guard()
    owner_id = int(sys.argv[1]) if len(sys.argv) > 1 else 999999
    batches = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    url = connect_url()
    engine = create_engine(url, pool_pre_ping=True)
    summary: List[Dict[str, Any]] = []
    with engine.begin() as conn:
        ensure_not_prod(conn)
        # Baseline plan before inserts
        baseline = measure_plan(conn, owner_id)
        count_before = conn.execute(text("SELECT COUNT(*) FROM receipts WHERE owner_id=:o"), {"o": owner_id}).scalar()
        summary.append({"batch": 0, "rows": count_before, **baseline})
        for b in range(1, batches + 1):
            insert_batch(conn, owner_id, b)
            # Force stats update for planner if needed
            conn.execute(text("ANALYZE receipts"))
            m = measure_plan(conn, owner_id)
            rows = conn.execute(text("SELECT COUNT(*) FROM receipts WHERE owner_id=:o"), {"o": owner_id}).scalar()
            summary.append({"batch": b, "rows": rows, **m})
    # Print human summary
    print(f"Load test summary owner_id={owner_id}")
    for row in summary:
        print(f"batch={row['batch']} rows={row['rows']} index={row['used_index']} time_ms={row['execution_time_ms']}")
        if row["used_index"]:
            break  # earliest crossover displayed; stop early
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
