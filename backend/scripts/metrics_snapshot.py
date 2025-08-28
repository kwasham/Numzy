"""Metrics snapshot utility.

Captures Postgres table and index statistics for lightweight observability.

Usage:
  docker compose run --rm api python scripts/metrics_snapshot.py [--json]

Output includes:
  - Table row counts (live + dead) and sizes
  - Index scan counts & sizes
  - Distinct owners & receipts per owner distribution percentiles

No extensions required; bloat estimation intentionally omitted (would require
pgstattuple). You can export JSON for shipping to an external system.
"""
from __future__ import annotations

import os
import sys
import json
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy import create_engine, text


def _connect_url() -> str:
    url = os.environ.get("ALEMBIC_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL / ALEMBIC_DATABASE_URL required", file=sys.stderr)
        sys.exit(2)
    return url.replace("+asyncpg", "+psycopg")


def fetch_table_stats(conn) -> List[Dict[str, Any]]:
    q = text(
        """
        SELECT relname AS table,
               n_live_tup AS live_rows,
               n_dead_tup AS dead_rows,
               pg_relation_size(relid) AS table_bytes,
               pg_total_relation_size(relid) AS total_bytes
        FROM pg_stat_user_tables
        ORDER BY n_live_tup DESC;
        """
    )
    rows = conn.execute(q).mappings().all()
    for r in rows:
        r["table_size_pretty"] = conn.execute(text("SELECT pg_size_pretty(:v)"), {"v": r["table_bytes"]}).scalar()
        r["total_size_pretty"] = conn.execute(text("SELECT pg_size_pretty(:v)"), {"v": r["total_bytes"]}).scalar()
    return rows


def fetch_index_stats(conn) -> List[Dict[str, Any]]:
    q = text(
        """
        SELECT i.relname AS index,
               t.relname AS table,
               psui.idx_scan AS idx_scan,
               pg_relation_size(i.oid) AS index_bytes
        FROM pg_class i
        JOIN pg_index ix ON ix.indexrelid = i.oid
        JOIN pg_class t ON t.oid = ix.indrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        LEFT JOIN pg_stat_user_indexes psui ON psui.indexrelid = i.oid
        WHERE n.nspname='public'
        ORDER BY index_bytes DESC;
        """
    )
    rows = conn.execute(q).mappings().all()
    for r in rows:
        r["index_size_pretty"] = conn.execute(text("SELECT pg_size_pretty(:v)"), {"v": r["index_bytes"]}).scalar()
    return rows


def fetch_receipt_owner_distribution(conn) -> Dict[str, Any]:
    q = text("SELECT owner_id, COUNT(*) c FROM receipts GROUP BY owner_id")
    counts = [row[1] for row in conn.execute(q).all()]
    if not counts:
        return {"owners": 0, "summary": {}}
    counts_sorted = sorted(counts)
    def pct(p: float) -> int:
        if not counts_sorted:
            return 0
        k = int(round((p / 100.0) * (len(counts_sorted) - 1)))
        return counts_sorted[k]
    summary = {
        "min": counts_sorted[0],
        "p50": pct(50),
        "p90": pct(90),
        "p95": pct(95),
        "p99": pct(99),
        "max": counts_sorted[-1],
        "mean": round(statistics.mean(counts_sorted), 2),
    }
    return {"owners": len(counts_sorted), "summary": summary}


def main() -> int:
    as_json = "--json" in sys.argv
    url = _connect_url()
    engine = create_engine(url, pool_pre_ping=True)
    snapshot: Dict[str, Any] = {"timestamp": datetime.now(timezone.utc).isoformat()}
    with engine.begin() as conn:
        snapshot["tables"] = fetch_table_stats(conn)
        snapshot["indexes"] = fetch_index_stats(conn)
        snapshot["receipts_owner_distribution"] = fetch_receipt_owner_distribution(conn)
    if as_json:
        json.dump(snapshot, sys.stdout, indent=2)
    else:
        print("Snapshot @", snapshot["timestamp"])  # minimal header
        print("Tables:")
        for t in snapshot["tables"]:
            print(f"  {t['table']}: live={t['live_rows']} dead={t['dead_rows']} size={t['table_size_pretty']} total={t['total_size_pretty']}")
        print("Indexes (top by size):")
        for i in snapshot["indexes"][:10]:
            print(f"  {i['index']} on {i['table']}: scans={i['idx_scan']} size={i['index_size_pretty']}")
        dist = snapshot["receipts_owner_distribution"]
        print("Receipts / owner distribution:")
        if dist.get("owners"):
            s = dist["summary"]
            print(f"  owners={dist['owners']} min={s['min']} p50={s['p50']} p90={s['p90']} p95={s['p95']} p99={s['p99']} max={s['max']} mean={s['mean']}")
        else:
            print("  <no receipts>")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
