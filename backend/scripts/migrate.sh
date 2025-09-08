#!/usr/bin/env bash
# Lightweight helper to run Alembic migrations using ALEMBIC_DATABASE_URL from .env or existing env.
# Usage:
#   ./scripts/migrate.sh            # upgrades to head
#   ./scripts/migrate.sh current    # shows current revision
#   ./scripts/migrate.sh downgrade <rev>  # downgrades
# Safe: does not echo secrets.
set -euo pipefail
cd "$(dirname "$0")/.."  # move to backend root

COMMAND=${1:-upgrade}
TARGET=${2:-head}

if [[ -f .env ]]; then
  # Export only ALEMBIC_DATABASE_URL (avoid polluting environment with everything else)
  ALEMBIC_LINE=$(grep -E '^ALEMBIC_DATABASE_URL=' .env || true)
  if [[ -n "$ALEMBIC_LINE" ]]; then
    # shellcheck disable=SC2163
    export "${ALEMBIC_LINE}"
  fi
fi

if [[ -z "${ALEMBIC_DATABASE_URL:-}" ]]; then
  echo "[migrate] ALEMBIC_DATABASE_URL not set; export it or add to backend/.env" >&2
  exit 1
fi

case "$COMMAND" in
  current)
    alembic current
    ;;
  upgrade)
    alembic upgrade "$TARGET"
    ;;
  downgrade)
    alembic downgrade "$TARGET"
    ;;
  heads)
    alembic heads
    ;;
  history)
    alembic history | tail -n 20
    ;;
  *)
    echo "Unknown command: $COMMAND" >&2
    echo "Usage: ./scripts/migrate.sh [current|upgrade|downgrade|heads|history] [target]" >&2
    exit 1
    ;;
 esac
