# Polar metering failure catalog — symptom → cause → fix

Every entry here has produced a real silent-$0-billing incident or is a near-miss the diagnostic checks for. Match the symptom, confirm the cause with `scripts/diagnose.mjs`, apply the fix. Ordered by how often it's the culprit.

---

## 1. Invoice is $0 but events show `inserted:1` — aggregation property typo

**Symptom:** Events ingest fine (`{"inserted":1}`), the subscription is active, orders are created — all `$0`. `consumed_units` is 0.

**Cause:** The meter's `aggregation.property` doesn't byte-match the emitted `metadata` key. Classic: meter sums `cost_cent` (singular) while the app emits `cost_cents` (plural). The filter still matches by event **name**, so events flow and look healthy, but `sum` targets a non-existent property → 0. Casing (`costCents` vs `cost_cents`) and spaces do the same.

**Confirm:** diagnostic link "emitted metadata key matches meter aggregation property" → FAIL. Or by hand: `GET /v1/meters/{id}` `aggregation.property` vs `GET /v1/events/?customer_id=...` metadata keys.

**Fix:** The aggregation is **immutable once aggregating** (`PATCH` → `422`), so you usually fix the **emitter** to send the meter's existing property name — even if it's the misspelled one — because that fixes all existing subscriptions without re-pointing prices. Add a comment at the emitter so nobody "corrects" the spelling and re-breaks billing. Then re-emit and confirm `consumed_units` increments. Past events do NOT backfill.

---

## 2. `PATCH /v1/meters/{id}` returns 422 — meter aggregation is locked

**Symptom:** Trying to fix the property on the meter returns `422 "This field can't be updated because the meter is already aggregating events."`

**Cause:** Polar freezes a meter's aggregation once it has counted any event. By design.

**Fix:** Don't fight it. Match the emitter to the meter (entry 1). Creating a *new* meter is a last resort — it forces a new metered price and a migration of every existing subscription to it; the old meter and its subscriptions keep producing $0.

---

## 3. `consumed_units` is 0 but everything else looks right

**Symptom:** Filter matches, events exist, but the customer meter shows `consumed: 0`.

**Causes (check in order):** (a) aggregation property mismatch (entry 1) — most likely; (b) events ingested *before* the meter/aggregation existed and you're expecting backfill — there is none; (c) the events carry the property but as a **string** when `sum` expects a number — send numbers, not `"1"`; (d) you're reading a different environment than the events landed in (entry 6).

**Fix:** Run the diagnostic; it isolates a–d. Remember: only events ingested *after* the config is correct will count.

---

## 4. "It's billing, just small" — actually it's $0

**Symptom:** Assuming tiny charges when the real number is exactly 0.

**Cause:** Conflating local usage counters / dashboards with the Polar invoice. Your app's "total usage" can be accurate while Polar bills $0 because the meter isn't aggregating.

**Fix:** Trust `consumed_units` and `GET /v1/orders` `total_amount`, not your own dashboard, as the billing source of truth. The diagnostic reads both.

---

## 5. New users charged for their "free" credit — local credit not reconciled

**Symptom:** Once metering works, users are billed for usage that local logic treated as free signup credit.

**Cause:** The emitter sends the **full** cost to Polar while local code separately decrements a free-credit balance. The two ledgers don't talk, so the free tier is billed by Polar anyway.

**Fix:** Send Polar only the billable overflow: `billable = max(0, cost − remainingCreditBefore)`, computed atomically (read credit under a row lock in the same transaction as the decrement). Forward `billable` to ingestion; skip ingestion when it's 0. Alternatively configure a matching credit benefit on the Polar product and don't withhold locally — but pick exactly one source of truth.

---

## 6. Works in sandbox, $0 in production (or vice-versa)

**Symptom:** Behaves differently across environments, or prod moves no money.

**Cause:** A sandbox token / sandbox API base / sandbox product+meter IDs leaked into production (or the inverse). Sandbox and production are separate Polar orgs. A sandbox token in prod silently bills nothing.

**Fix:** One env switch driving base URL + token + product/meter IDs. Sandbox tokens commonly look like `polar_oat_…` on `sandbox-api.polar.sh`; verify with `GET /v1/customers/{id}` that the customer/org is the one you expect. The diagnostic takes `POLAR_SERVER=sandbox|production` — run it against both if unsure.

---

## 7. Diagnosis returns `insufficient_scope`

**Symptom:** `GET /v1/meters` or `/v1/orders` → `{"error":"insufficient_scope"}`.

**Cause:** The production **ingestion** token only needs `events:write`, so it's usually scoped down and can't read meters/orders.

**Fix:** Create a separate token with `meters:read` + `orders:read` (+ `customers:read`, `events:read`) just for diagnosis. Don't widen the production ingestion token. Keep the diagnostic token in a local file, never echo it into logs or chat, never commit it.

---

## 8. Customer linked but usage orphaned

**Symptom:** Subscription exists, events ingest, but a specific customer's usage never bills.

**Cause:** Events sent with a `customer_id`/`external_customer_id` that doesn't resolve to a linked Polar customer, or the customer was never created. Orphaned events aren't billed.

**Fix:** Ensure the Polar customer exists and its `external_id` maps to your tenant (set `external_customer_id` at checkout; store the returned `customer_id`). Only emit usage for customers you've confirmed are linked.

---

## 9. Webhook 200-ack on failure loses the link forever

**Symptom:** A subscription exists in Polar but your DB never recorded the `customer_id`; usage for that org silently drops.

**Cause:** The webhook handler caught a resolution failure and still returned `200`. Polar marks delivery successful and never retries, so the one chance to link the customer is gone.

**Fix:** Return non-2xx whenever customer/org resolution fails so Polar retries. Keep the handler idempotent (dedupe by `webhook-id`) so retries are safe. Verify the HMAC signature.

---

## 10. Ingestion failures vanish

**Symptom:** Occasional gaps in metered usage with no error surfaced.

**Cause:** Fire-and-forget ingestion — failures are logged and swallowed, never retried. A Polar API blip drops events permanently.

**Fix:** At minimum, log+alert on ingestion failure. If usage is high-value, put ingestion behind a durable queue with retry. Accept the tradeoff explicitly rather than discovering it as missing revenue.

---

## The one-line rule

After **any** billing change, emit one event and confirm `consumed_units` went up. Unit tests on the emitter are necessary but not sufficient — the meter config lives in the Polar dashboard, outside your repo, and is the half that silently breaks.
