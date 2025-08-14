#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT_DIR/scripts/run-be-fe.sh"

chmod +x "$RUNNER"

echo "[restart-be-fe] Restarting backend and frontend with rebuild"
"$RUNNER" --fresh --rebuild
