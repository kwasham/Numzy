# Stripe MCP — Prompt Pack (Test Mode)

These prompts are designed for VS Code Chat with the **Stripe MCP server** enabled and **test** keys.
Use one block at a time. Replace placeholders like `<PRICE_ID>`, `<CUS_ID>`, `<SUB_ID>`.

---

## Seed: Pro product + monthly/yearly prices
```
Create a product "Numzy Pro" and two recurring prices: $19/mo and $190/yr.
Currency: USD. Trial: none.
Respond **only** with JSON:

{
  "product": "<prod_...>",
  "monthly_price": "<price_...>",
  "yearly_price": "<price_...>"
}
```
> Paste the JSON into `scripts/stripe_env_write.py` (see README) to populate your `.env.development`.

---

## Seed: Team product (seat-based)
```
Create a product "Numzy Team (per seat)" and a recurring price of $49 per seat monthly.
Include the usage_type as "licensed" (per unit). Quantity is seats.
Respond only with JSON: { "product": "...", "team_monthly_price": "..." }
```

---

## Checkout (subscription) for a price
```
Create a Checkout Session (mode=subscription) for price <PRICE_ID>.
success_url: http://localhost:3000/billing/success?session_id={CHECKOUT_SESSION_ID}
cancel_url: http://localhost:3000/pricing
allow_promotion_codes: true
Return **only**: { "url": "<https://checkout.stripe.com/...>" }
```

---

## Customer Portal for a customer
```
Create a Customer Portal session for customer <CUS_ID>.
return_url: http://localhost:3000/settings/billing
Return only: { "url": "<https://billing.stripe.com/...>" }
```

---

## Test Clock simulation (fast-forward renewals)
```
1) Create a test clock named "numzy-sub".
2) Create a customer attached to that clock.
3) Create a subscription for price <PRICE_ID> for that customer.
4) Advance the clock by 35 days.
Return JSON:
{
  "customer": "<cus_...>",
  "subscription": "<sub_...>",
  "status": "<active|past_due|...>",
  "current_period_end": "<iso8601>"
}
```

---

## Inspect a subscription
```
Get subscription by id <SUB_ID> and return:
{ "status": "...", "price": "<price_id>", "current_period_end": "<iso8601>" }
```

---

## Cancel (at period end)
```
Update subscription <SUB_ID> with cancel_at_period_end=true.
Return: { "subscription": "<sub_...>", "cancel_at_period_end": true }
```

---

### Notes
- Keep **test mode** keys configured in your MCP server env until you go live.
- Use the Stripe CLI for local webhooks:
  `stripe listen --forward-to localhost:8000/webhooks/stripe`
