---
id: "F28-cli-rental-quote-rules"
title: "Rental quote command with weekend and deposit rules"
status: planned
complexity: high
depends-on: []
---

# F28 Rental quote command with weekend and deposit rules

## Context

`bench-cli` currently has greeting and version commands only. The task:
add a `rental-quote` command that reads an equipment rental request, prices it
from `data/rental-rules.json`, validates combined inventory, and prints one
exact integer-cents quote.

Rental quotes are operational contracts: duplicate item rows must be combined
before stock validation, weekend surcharge rules must be deterministic, and
success output must stay machine-readable without extra fields.

## Requirements

- [ ] `bench-cli rental-quote --input <path>` reads JSON shaped as `{ "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "coupon": string | null, "protection": boolean, "items": [{ "sku": string, "qty": number }] }`.
- [ ] Item daily rates, stock, deposits, weekend surcharge percent, protection daily price, and coupons come from `data/rental-rules.json`. Do not hardcode those values in the command implementation.
- [ ] `rental_days` is the number of calendar days from `start_date` inclusive to `end_date` exclusive, using UTC date math. `end_date` must be after `start_date`.
- [ ] A rental day is a weekend day when its UTC day is Saturday or Sunday.
- [ ] Combine duplicate SKUs before validating stock and before computing item rows. The output `items` array must contain one row per SKU in first-seen order.
- [ ] Validation happens before any quote is printed. Invalid JSON, missing `items`, unknown SKU, non-positive or non-integer `qty`, combined quantity over stock, invalid date format, `end_date` not after `start_date`, unknown coupon, or non-boolean `protection` exits `2` and writes exactly one JSON error object to stderr.
- [ ] Combined quantity over stock uses exact error shape `{ "error": "unavailable_inventory", "sku": string, "available": number, "requested": number }`.
- [ ] `subtotal_cents` is the sum of `daily_cents * combined_qty * rental_days` for all item rows.
- [ ] `weekend_surcharge_cents` is the sum of `Math.round(daily_cents * combined_qty * weekend_days * weekend_surcharge_percent / 100)` for all item rows.
- [ ] `discount_cents` is `Math.round((subtotal_cents + weekend_surcharge_cents) * coupon.percent / 100)` when a coupon is present and `rental_days >= coupon.min_rental_days`; otherwise `0`.
- [ ] `protection_cents` is `protection_daily_cents * total_combined_qty * rental_days` when `protection` is true; otherwise `0`.
- [ ] `deposit_cents` is the sum of `deposit_cents * combined_qty` for all item rows. Deposits are never discounted.
- [ ] `total_cents = subtotal_cents + weekend_surcharge_cents - discount_cents + protection_cents + deposit_cents`.
- [ ] On success, write exactly one JSON object to stdout and no stderr. Keys: `rental_days`, `weekend_days`, `subtotal_cents`, `weekend_surcharge_cents`, `discount_cents`, `protection_cents`, `deposit_cents`, `total_cents`, `items`.
- [ ] Each output item row has keys `sku`, `qty`, `rental_cents`, `deposit_cents`. `rental_cents` is `daily_cents * combined_qty * rental_days`, and row `deposit_cents` is the item's deposit times combined quantity.
- [ ] `tests/cli.test.js` is updated. Existing tests still pass AND at least two new tests cover `rental-quote`: one successful quote and one validation failure.

## Constraints

- **No new npm dependencies.**
- **No floating-money output.** All public amounts are integer cents.
- **No silent catches.** If parsing or file reading fails, emit a visible JSON error to stderr and exit `2`.
- **No extra stdout/stderr text** on the success path; downstream tooling parses stdout as JSON.
- **Lifecycle note.** The harness's DOCS phase flips this spec's frontmatter `status` after implementation completes — that is benchmark lifecycle bookkeeping, not a scope violation.

## Out of Scope

- Persisting reservations or mutating inventory.
- Hourly pricing, time zones beyond UTC date math, holidays, or blackout dates.
- Taxes, shipping, currencies, or payment capture.
- Adding server routes or web UI.
- Touching `server/`, `web/`, or `tests/server.test.js`.

## Verification

- `node --test tests/cli.test.js` exits 0.
- A Friday-to-Tuesday rental counts four rental days and two weekend days.
- Duplicate SKUs are combined before stock validation and pricing.
- A successful quote emits exact integer-cent weekend surcharge, discount, protection, deposit, and total fields.
- A combined quantity over stock exits `2`, prints one JSON error to stderr, and prints no stdout.
- The unavailable inventory error object includes `error`, `sku`, `available`, and `requested`.
- Changing `data/rental-rules.json` rates, deposits, or surcharge settings changes command output without code changes.
- `git diff --stat` shows only `bin/cli.js` and `tests/cli.test.js` touched (the rental rules seed comes from setup, not the arm).
