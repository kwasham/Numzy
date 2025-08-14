#!/usr/bin/env bash
set -euo pipefail

# Numzy dev runner: brings up backend infra (Docker Compose) and starts frontend dev (pnpm)
# Usage:
#   ./scripts/run-be-fe.sh [--rebuild] [--fresh] [--no-frontend] [--no-db]
# Notes:
#   - Uses root docker-compose.yml with profiles: infra, app, and optionally local-db
#   - Starts frontend dev in background and writes PID to frontend-dev.pid

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"

REBUILD=0
FRESH=0
NO_FE=0
NO_DB=0

while [[ ${1:-} ]]; do
  case "$1" in
    --rebuild) REBUILD=1 ;;
    --fresh) FRESH=1 ;;
    --no-frontend|--no-fe) NO_FE=1 ;;
    --no-db) NO_DB=1 ;;
    -h|--help)
      echo "Usage: $0 [--rebuild] [--fresh] [--no-frontend] [--no-db]"
      exit 0
      ;;
    *) echo "Unknown option: $1" && exit 1 ;;
  esac
  shift
done

# Pick docker compose command
if command -v docker-compose >/dev/null 2>&1; then
  DC=(docker-compose -f "$COMPOSE_FILE")
else
  DC=(docker compose -f "$COMPOSE_FILE")
fi

profiles=(--profile infra --profile app)
if [[ $NO_DB -eq 0 ]]; then
  profiles+=(--profile local-db)
fi

echo "[run-be-fe] Using compose file: $COMPOSE_FILE"

if [[ $FRESH -eq 1 ]]; then
  echo "[run-be-fe] Fresh start: docker compose down -v"
  "${DC[@]}" down -v --remove-orphans || true
fi

UP_FLAGS=(-d --remove-orphans)
if [[ $REBUILD -eq 1 ]]; then
  UP_FLAGS+=(--build)
fi

echo "[run-be-fe] Bringing up backend services (${profiles[*]})"
"${DC[@]}" ${profiles[*]} up "${UP_FLAGS[@]}"

# Wait for API to be reachable on port 8000 (best-effort)
echo "[run-be-fe] Waiting for API on http://localhost:8000 ..."
for i in {1..30}; do
  if curl -sSf "http://localhost:8000/" >/dev/null 2>&1 || nc -z localhost 8000 >/dev/null 2>&1; then
    echo "[run-be-fe] API is reachable"
    break
  fi
  sleep 1
done || true

if [[ $NO_FE -eq 0 ]]; then
  echo "[run-be-fe] Starting frontend dev server (pnpm dev)"
  if command -v pnpm >/dev/null 2>&1; then
    PKG_MGR=pnpm
  elif command -v npm >/dev/null 2>&1; then
    PKG_MGR=npm
  else
    echo "[run-be-fe] ERROR: Neither pnpm nor npm found in PATH" >&2
    exit 1
  fi

  export NEXT_TELEMETRY_DISABLED=1
  (
    cd "$FRONTEND_DIR"
    if [[ "$PKG_MGR" == "pnpm" ]]; then
      pnpm install
      nohup pnpm dev > frontend-dev.log 2>&1 & echo $! > frontend-dev.pid
    else
      npm install
      nohup npm run dev > frontend-dev.log 2>&1 & echo $! > frontend-dev.pid
    fi
  )
  echo "[run-be-fe] Frontend started. Logs: frontend/frontend-dev.log, PID: $(cat "$FRONTEND_DIR/frontend-dev.pid" 2>/dev/null || echo 'n/a')"
fi

cat <<EOF

[run-be-fe] Dev environment is up:
  - Frontend:   http://localhost:3000
  - API:        http://localhost:8000 (FastAPI docs usually at /docs)
  - MCP server: http://localhost:8002
  - Redis:      localhost:6379
  - MinIO:      http://localhost:9000 (console: :9001)
  - Postgres:   localhost:5432 (when --no-db not used)

Tips:
  - To view container logs: ${DC[*]} logs -f api worker mcp
  - To stop everything:     ${DC[*]} down --remove-orphans
  - To nuke volumes:        ${DC[*]} down -v

EOF
