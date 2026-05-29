---
name: polar-billing-setup
description: Set up, integrate, and DEBUG Polar (polar.sh) usage-based / metered billing the right way — events ingestion, meters, metered prices, checkout, webhooks, and free-credit reconciliation. Use this whenever the user mentions Polar billing, usage-based or metered billing, "ingest events to Polar", a Polar meter, a metered price, or — critically — when billing looks broken: "Polar isn't charging", "my invoice is $0", "usage events aren't billing", "consumed_units is 0", "metering not working", or "why are customers not being charged". This skill encodes the silent-failure traps that make Polar metering quietly bill $0, and ships a diagnostic script that tells you exactly where the chain is broken. Prefer it over guessing whenever Polar metered billing is involved, even if the user doesn't name the specific failure.
allowed-tools: Read, Write, Edit, Bash
argument-hint: [setup | verify | diagnose --customer <id>]
---

# Polar usage-based billing — setup & verification

Polar metered billing is a **chain**, and any single broken link silently bills **$0** with no error. Events still return `inserted: 1`, the dashboard still shows the subscription as active, orders still get created — they're just all `$0`. The failure is invisible unless you check the one number that matters: the meter's `consumed_units`.

This skill exists because that chain is easy to misconfigure and the failures are silent. Read this top section always; pull in `references/` and run `scripts/diagnose.mjs` as the task dictates.

## The billing chain (every link must hold)

```
app emits event  ─►  meter FILTER matches it  ─►  meter AGGREGATION sums a property
   (name +              (by event name)            that EXISTS on the event
    metadata)                                              │
                                                           ▼
customer is linked  ◄─  metered PRICE is attached  ◄─  consumed_units > 0
to a subscription       to the meter (not flat/free)
        │
        ▼
   invoice charges at cycle end
```

Break any arrow and the invoice is `$0`. The most common break — and the one that burns hours — is the **aggregation property name not matching the emitted metadata key** (a `cost_cent` vs `cost_cents` typo, a casing/spacing mismatch). The filter still matches by event name, so events flow in and look fine, but the sum targets a property that doesn't exist, so `consumed_units` stays 0.

## Golden rules (the why behind each)

1. **The aggregation property must byte-match the emitted metadata key.** Polar sums `metadata.<property>`; if the emitter sends `cost_cents` and the meter sums `cost_cent`, the sum is over a missing field → 0. Decide the exact key ONCE and assert it on both ends. Singular/plural/camelCase/snake_case are different keys.

2. **A meter's aggregation is immutable once it has aggregated events.** `PATCH /v1/meters/{id}` on `aggregation` returns `422 "can't be updated because the meter is already aggregating events"`. So you cannot fix a property typo on the meter after go-live. Either get it right at creation, or — the cheaper fix — **change the emitter to match the meter's existing (even misspelled) property**, because that fixes existing subscriptions without re-pointing prices. Recreating the meter means creating a new price and migrating every existing subscription. Document any locked-in misspelling at the emitter so nobody "corrects" it and re-breaks billing.

3. **`inserted: 1` is NOT proof of billing.** It means the event was accepted, not metered. The only proof is `consumed_units > 0` on the customer's meter (`GET /v1/customers/{id}/state` or `GET /v1/meters/{id}/quantities`). Always verify after a change.

4. **Polar does not backfill.** Events ingested before the meter/aggregation/price was correct are NOT retro-counted when you fix the config. Only events after the fix aggregate. Plan a manual order/credit adjustment if past usage must be recovered.

5. **The price must be a metered price bound to the meter.** A product can have a `free`/`fixed` price AND a `metered_unit` price; only the `metered_unit` one with the right `meter_id` produces usage charges. Verify `amount_type: "metered_unit"` and `meter_id` match.

6. **Usage attributes to a linked customer.** Events carry `customer_id` (Polar's id) or `external_customer_id` (your id, set at checkout). If the customer isn't created/linked, the usage is orphaned and never billed. Confirm the customer exists and its `external_id` maps back to your tenant.

7. **Sandbox ≠ production.** Token, API base (`sandbox-api.polar.sh` vs `api.polar.sh`), and product/meter IDs all differ per environment. A sandbox token in prod means no real money moves — and it fails silently. Drive the base + IDs off one env switch.

8. **Token scopes are split.** Ingestion needs `events:write`; reading meters/orders for diagnosis needs `meters:read` / `orders:read`. The minimal ingestion token usually CANNOT read meters, so diagnosis returns `insufficient_scope` — provision a separate read-scoped token for debugging (never widen the production ingestion token just to debug).

9. **Reconcile local free credit with Polar.** If you grant local "first $X free" credit, the emitter must send Polar only the **billable overflow** (`max(0, cost − remainingCredit)`), or Polar will bill the free tier too. Conversely, if Polar grants the credit (a credit benefit), don't also withhold locally. Pick one source of truth and net consistently.

10. **Webhooks must fail loud, not 200-ack.** Returning `200` when customer resolution fails makes Polar treat delivery as successful and never retry — the link is lost forever. Return non-2xx on unresolved linkage; keep handlers idempotent (dedupe by event id).

## Workflow

**Setup a new integration** → read `references/setup.md` and follow it in order (meter → product+metered price → checkout → webhook → ingestion). Get the property name and aggregation right the first time (rule 2).

**Add metering to an existing integration** → confirm the meter's exact `aggregation.property`, then make the emitter send that exact key. Don't invent a "nicer" key.

**Debug "$0 invoice" / "not charging" / "consumed_units is 0"** → run the diagnostic FIRST, before theorizing:

```bash
POLAR_ACCESS_TOKEN=<read-scoped token> POLAR_SERVER=production \
  node scripts/diagnose.mjs --customer <polar_customer_id> --event-name <name>
```

It reports, link by link, where the chain breaks: token scope, meter filter+aggregation, whether recent events' metadata keys actually match the aggregation property, `consumed_units`, the product's price type, and recent order totals. Read its verdict, then fix the one broken link. See `references/gotchas.md` for the full failure catalog mapped to symptoms.

**After ANY fix** → verify with rule 3: emit one real (or synthetic `cost:1`) event and confirm `consumed_units` increments. A passing unit test on the emitter is necessary but not sufficient — the meter config lives in the Polar dashboard, outside your repo.

## Reference files

- `references/setup.md` — step-by-step correct setup (meter, product, metered price, checkout, webhook, ingestion), with the exact API shapes.
- `references/gotchas.md` — the full silent-failure catalog: symptom → cause → fix, including everything that produced a real $0-billing incident.

## Diagnostic script

`scripts/diagnose.mjs` — Node 18+ (global `fetch`). Read-only. Walks the whole chain for one customer and prints a per-link PASS/FAIL verdict. This is the fastest path from "billing seems broken" to "here is the exact broken link." Requires a token with `meters:read` + `orders:read` (see rule 8).
