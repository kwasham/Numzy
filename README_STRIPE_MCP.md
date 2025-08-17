# Stripe MCP — Quick Start (Test Mode)

This pack helps you drive **Stripe Subscriptions** from VS Code Chat (via **Stripe MCP server**) and
persist the returned IDs into your repo’s env files.

## Files

- `.github/prompts/stripe-mcp.md` — curated prompts for products/prices, Checkout, Portal, Test Clocks, etc.
- `scripts/stripe_env_write.py` — CLI to upsert Stripe IDs into an `.env` file (idempotent).
- `scripts/stripe_cli_dev.sh` — helper to run `stripe listen` for local webhook forwarding.

## 1) Enable Stripe MCP in VS Code (test mode)

In your VS Code settings (user or workspace):

```json
{
  "mcpServers": {
    "stripe": {
      "command": "npx",
      "args": ["-y", "@stripe/mcp", "--tools=all"],
      "env": { "STRIPE_SECRET_KEY": "sk_test_***" }
    }
  }
}
```

## 2) Seed products & prices in Chat

Open **`.github/prompts/stripe-mcp.md`**, copy the first block, and paste into Chat.
You’ll get JSON like:

```json
{ "product":"prod_123", "monthly_price":"price_111", "yearly_price":"price_222" }
```

## 3) Write the IDs to your env

Pipe that JSON into the script to upsert keys into `.env.development` (or any env path):

```bash
echo '{"product":"prod_123","monthly_price":"price_111","yearly_price":"price_222"}'   | python scripts/stripe_env_write.py --env .env.development --json -       --map product=STRIPE_PRODUCT_PRO            monthly_price=STRIPE_PRICE_PRO_MONTHLY            yearly_price=STRIPE_PRICE_PRO_YEARLY
```

You can also set pairs directly:

```bash
python scripts/stripe_env_write.py --env .env.development   --set STRIPE_PRICE_TEAM_MONTHLY=price_333
```

## 4) Run local webhooks

```bash
./scripts/stripe_cli_dev.sh        # forwards to http://localhost:8000/webhooks/stripe
# copy the printed signing secret into STRIPE_WEBHOOK_SECRET in your env
```

## 5) Try a Checkout Session (test card 4242 4242 4242 4242)

Use the "Checkout (subscription) for a price" prompt with your `<PRICE_ID>` and open the returned URL.

## 6) Fast-forward renewals with Test Clocks

Use the "Test Clock simulation" prompt. Your FastAPI webhook should receive renewal events; verify your DB updates.

---

### Notes

- Keep these **test** IDs separate from live keys/IDs.
- MCP is for **dev/QA**. In production, create sessions in your backend and verify webhooks server-side.
