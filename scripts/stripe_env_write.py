#!/usr/bin/env python3
"""
Upsert Stripe IDs into an .env file (e.g., .env.development).

Usage examples:

1) Pipe JSON from MCP (Pro product + prices):
   echo '{"product":"prod_123","monthly_price":"price_111","yearly_price":"price_222"}' \
     | python scripts/stripe_env_write.py --env .env.development --json - \
       --map product=STRIPE_PRODUCT_PRO \
             monthly_price=STRIPE_PRICE_PRO_MONTHLY \
             yearly_price=STRIPE_PRICE_PRO_YEARLY

2) Direct key=value pairs:
   python scripts/stripe_env_write.py --env .env.development \
     --set STRIPE_PRICE_TEAM_MONTHLY=price_333

Behavior:
- Creates the env file if missing.
- Preserves existing lines, updates only the mapped keys (idempotent).
- Adds keys at the end if not present.
"""

import sys, os, argparse, json, re
from typing import Dict

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--env", required=True, help="Path to .env file (e.g., .env.development)")
    p.add_argument("--json", help="Path to JSON input or '-' to read from stdin")
    p.add_argument("--map", nargs="*", default=[], help="JSONKey=ENV_KEY mappings")
    p.add_argument("--set", nargs="*", default=[], help="Direct key=value pairs")
    return p.parse_args()

def load_json_arg(path: str):
    if not path:
        return {}
    data = sys.stdin.read() if path == "-" else open(path, "r", encoding="utf-8").read()
    return json.loads(data) if data.strip() else {}

def upsert_env(path: str, updates: Dict[str,str]):
    lines = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

    # Build a dict of existing keys -> index
    key_to_idx = {}
    for idx, line in enumerate(lines):
        if not line or line.strip().startswith("#"):
            continue
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line)
        if m:
            key_to_idx[m.group(1)] = idx

    for key, val in updates.items():
        if key in key_to_idx:
            idx = key_to_idx[key]
            lines[idx] = f"{key}={val}"
        else:
            lines.append(f"{key}={val}")

    content = "\n".join(lines) + ("\n" if lines and not lines[-1].endswith("\n") else "")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    args = parse_args()
    updates = {}

    # From --json + --map
    j = load_json_arg(args.json) if args.json else {}
    for mapping in args.map:
        if "=" not in mapping:
            print(f"Invalid --map entry: {mapping}", file=sys.stderr)
            sys.exit(2)
        jkey, ekey = mapping.split("=", 1)
        if jkey in j:
            updates[ekey] = str(j[jkey])

    # From --set pairs
    for pair in args.set:
        if "=" not in pair:
            print(f"Invalid --set entry: {pair}", file=sys.stderr)
            sys.exit(2)
        k, v = pair.split("=", 1)
        updates[k] = v

    if not updates:
        print("No updates provided. Use --json/--map and/or --set.", file=sys.stderr)
        sys.exit(2)

    upsert_env(args.env, updates)
    print(f"Updated {args.env} with {len(updates)} key(s).")

if __name__ == "__main__":
    main()
