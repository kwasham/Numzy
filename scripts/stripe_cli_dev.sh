#!/usr/bin/env bash
# Helper to run Stripe CLI webhook forwarding in dev.
# Usage: ./scripts/stripe_cli_dev.sh [PORT]
# Default FastAPI port: 8000
set -euo pipefail

PORT=${1:-8000}
TARGET="localhost:${PORT}/webhooks/stripe"

if ! command -v stripe >/dev/null 2>&1; then
  echo "Stripe CLI not found. Install from https://stripe.com/docs/stripe-cli" >&2
  exit 1
fi

echo "Forwarding Stripe events to http://${TARGET} ..."
stripe listen --forward-to "${TARGET}"
