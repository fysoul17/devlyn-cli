---
complexity: medium
---

# Generated criteria — bench-cli payout command

## Requirements

- Add a `payout --input <path>` subcommand to `bin/cli.js`. It reads ledger events from the JSON file at `<path>` (`{ "events": [{ "id": string, "merchant_id": string, "type": "charge" | "refund" | "dispute", "amount_cents": number }] }`) and reads processing fee percent, fixed fee cents, dispute fee cents, reserve percent, and minimum payout threshold cents from `data/payout-rules.json`. Rule values must never be hardcoded in `bin/cli.js` — changing `data/payout-rules.json` must change the command's output with no code change.
- Idempotent event handling: an event `id` seen again with byte-identical JSON content is applied only once (deduplicated). The same `id` seen again with different JSON content is a conflicting duplicate: the command must exit `2`, write nothing to stdout, and write exactly the JSON object `{ "error": "conflicting_duplicate", "id": string }` to stderr, before any totals are computed or printed. After identical duplicates are removed, merchant rows are ordered by first-seen merchant.
- Per-merchant accounting, applied in event order after dedup: a `charge` adds its `amount_cents` to `gross_charge_cents` and adds `Math.round(amount_cents * processing_fee_percent / 100) + fixed_fee_cents` to `processing_fee_cents`. A `refund` adds its `amount_cents` to `refund_cents` and does NOT reverse any processing fee. A `dispute` adds its `amount_cents` to `dispute_cents` and adds one `dispute_fee_cents` to the merchant's dispute fee total. Then: `net_before_reserve = gross_charge_cents - refund_cents - dispute_cents - processing_fee_cents - dispute_fee_cents`; `reserve_cents = Math.round(net_before_reserve * reserve_percent / 100)` when `net_before_reserve > 0`, else `0`; `payout_cents = net_before_reserve - reserve_cents`. If `0 < payout_cents < minimum_payout_cents`, keep the merchant row, add that original positive `payout_cents` amount into `reserve_cents`, and set `payout_cents` to `0`.
- On success, stdout is exactly one JSON object with only the keys `total_payout_cents`, `total_processing_fee_cents`, `total_dispute_fee_cents`, `total_reserve_cents`, and `merchants`, and nothing is written to stderr. Each `merchants` row has exactly the keys `merchant_id`, `gross_charge_cents`, `refund_cents`, `dispute_cents`, `processing_fee_cents`, `dispute_fee_cents`, `reserve_cents`, `payout_cents`. Every top-level total equals the sum of the corresponding final merchant field. Every public amount is an integer number of cents.
- Any of the following is a validation failure: an event with an unknown `type`, a missing `merchant_id`, a missing `id`, a non-positive or non-integer `amount_cents`, a missing top-level `events` array, invalid JSON in the input file, or an unreadable input file. Each must exit `2`, write exactly one JSON error object to stderr, and write nothing to stdout. Parsing and file-read failures must surface as a JSON error object, not a silent catch (e.g. no bare `try { } catch { }` that swallows the error).
- Update `tests/cli.test.js` so the existing `hello`/`version` tests still pass, and add at least two new tests for the `payout` command: one exercising a successful payout and one exercising a validation failure.

## Constraints

- Only `bin/cli.js` and `tests/cli.test.js` may change. Do not touch `server/` or `web/` files.
- Do not add dependencies (`package.json` `dependencies`/`devDependencies` stay as-is).
- Payout rule values (`processing_fee_percent`, `fixed_fee_cents`, `dispute_fee_cents`, `reserve_percent`, `minimum_payout_cents`) come from `data/payout-rules.json` at run time, never inlined as literals in `bin/cli.js`.

## Out of Scope

- Any file other than `bin/cli.js` and `tests/cli.test.js`.
- Any CLI command or flag not named above (`hello`, `version`, `--help` stay unchanged).
- Persisting payout results anywhere; the command only reads its input file and `data/payout-rules.json` and prints to stdout/stderr.

<!-- devlyn:verification -->
## Verification

- `node --test tests/` — full suite (existing hello/version tests plus the new payout tests) exits `0`.
- `node bin/cli.js payout --input <tmp-file>` for a valid events file prints exactly one JSON object to stdout with keys `total_payout_cents`, `total_processing_fee_cents`, `total_dispute_fee_cents`, `total_reserve_cents`, `merchants`, integer-cent totals matching the values in `data/payout-rules.json`, and writes nothing to stderr.
- `node bin/cli.js payout --input <tmp-file-with-same-id-different-content>` exits `2`, writes nothing to stdout, and writes exactly `{"error":"conflicting_duplicate","id":"<id>"}` to stderr.
- `node bin/cli.js payout --input <tmp-file-with-missing-merchant_id-or-unknown-type-or-non-integer-amount_cents>` exits `2`, writes nothing to stdout, and writes exactly one JSON error object to stderr.

```json
{"verification_commands": [{"cmd": "node --test tests/", "exit_code": 0}]}
```
