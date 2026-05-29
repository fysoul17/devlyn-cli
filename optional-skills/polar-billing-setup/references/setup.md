# Correct setup order — Polar usage-based billing

Set these up in order. The ordering matters because the price binds to the meter, and the emitter must match the meter's aggregation property (which is immutable after the first event — see rule 2 in SKILL.md).

## 0. Decide the contract first (on paper)

Before clicking anything, fix three strings and never deviate:

- **event name** — e.g. `compute-usage`
- **metadata property** to aggregate — e.g. `cost_cents` (pick the spelling now; you cannot change it on the meter later)
- **unit semantics** — what one unit costs. If the meter sums `cost_cents` (integer cents of cost) and the price is `unit_amount = 1` (1 cent/unit), then charge = cents-of-cost = the dollar cost. Keep the math trivially invertible.

## 1. Meter (dashboard or API)

A meter has a **filter** (which events it counts) and an **aggregation** (what number it produces).

```
POST /v1/meters
{
  "name": "compute-usage",
  "filter": { "conjunction": "and", "clauses": [
    { "conjunction": "or", "clauses": [
      { "property": "name", "operator": "eq", "value": "compute-usage" }
    ]}
  ]},
  "aggregation": { "func": "sum", "property": "cost_cents" }   // ← property MUST equal the emitted metadata key
}
```

- `func` is `count` | `sum` | `avg` | `min` | `max`. For `count`, `property` is irrelevant. For the rest, `property` must be a metadata key present on the events.
- **This `aggregation` cannot be edited once events have been counted** (`422`). Triple-check the property spelling here.

## 2. Product + metered price

```
POST /v1/products
{ "name": "Pay-as-you-go", "recurring_interval": "month",
  "prices": [
    { "amount_type": "free" },                                 // $0/mo base
    { "amount_type": "metered_unit", "unit_amount": 1,         // 1 cent per unit
      "meter_id": "<meter id from step 1>" }                   // ← binds price to the meter
  ]
}
```

- Without a `metered_unit` price bound to the meter, usage never turns into money.
- `unit_amount` is per unit in the smallest currency unit (supports fractional via decimal string).

## 3. Checkout (links a customer to the subscription)

```
POST /v1/checkouts/
{ "products": ["<product id>"],
  "customer_email": "<email>",
  "external_customer_id": "<your tenant/org id>",   // ← so webhooks + events map back to you
  "success_url": "https://app.example.com/success" }
```

- `external_customer_id` is the bridge: later you read it back from the Polar customer (`external_id`) to link the Polar `customer_id` to your tenant. Set it, always.

## 4. Webhook (subscription lifecycle → your DB)

Handle `subscription.created` / `.updated` / `.canceled` / `.revoked`. On `created`/`updated`, resolve your org from `customer_id` (DB lookup, then `GET /v1/customers/{id}` → `external_id` fallback) and store the Polar `customer_id` on your org.

- **Fail loud.** If you can't resolve the org, return non-2xx so Polar retries. A `200` ack on failure loses the link permanently.
- Verify the `webhook-signature` HMAC; dedupe by `webhook-id` for idempotency.

## 5. Ingestion (emit usage)

```
POST /v1/events/ingest
{ "events": [{
    "name": "compute-usage",                 // ← must match the meter filter
    "customer_id": "<polar customer id>",     // (or external_customer_id)
    "metadata": { "cost_cents": <amount> }    // ← key MUST match meter aggregation.property
}]}
```

- Emit only the **billable** amount. If you grant local free credit, send `max(0, cost − remainingCredit)` so the free tier isn't billed (rule 9).
- Ingestion is fire-and-forget on most integrations; failures are logged, not retried. Monitor for `ingestion failed` and decide if you need a retry/queue.

## 6. Verify (do NOT skip)

```
node scripts/diagnose.mjs --customer <id> --event-name compute-usage
```

Emit one event, then confirm `consumed_units > 0`. `inserted:1` is not enough. There is no backfill, so verify before you assume past usage will be captured.

## Environment switch

Drive everything off one flag:

```
const PROD = process.env.NODE_ENV === "production";
const BASE = PROD ? "https://api.polar.sh" : "https://sandbox-api.polar.sh";
const PRODUCT_ID = PROD ? "<prod product>" : "<sandbox product>";
// token + webhook secret come from env per environment
```

Sandbox and production are separate orgs with separate tokens, products, and meters. A sandbox token in prod moves no real money and fails silently.
