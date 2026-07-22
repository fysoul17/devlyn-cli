# Generated criteria — bench-cli payout command

Source: free-form goal (`.devlyn/goal.raw.txt`). Complexity: medium.

## Requirements

- Add a `payout` subcommand to `bin/cli.js`: `bench-cli payout --input <path>`, reading ledger events from the JSON file at `<path>` and printing merchant payout totals to stdout.
- Input shape: `{ "events": [{ "id": string, "merchant_id": string, "type": "charge" | "refund" | "dispute", "amount_cents": number }] }`. Validate every event; on an unknown `type`, missing `merchant_id`, missing `id`, non-positive or non-integer `amount_cents`, missing `events`, invalid JSON, or an unreadable input file, exit `2`, write exactly one JSON error object to stderr, and write nothing to stdout. Parsing/file-read failures must surface as JSON errors, not silent catches.
- Idempotency: events with the same `id` and identical JSON content are deduplicated and applied once. The same `id` with differing JSON content is a `conflicting_duplicate` — exit `2`, no stdout, stderr exactly `{ "error": "conflicting_duplicate", "id": string }`, checked before any totals are printed.
- Merchant ordering: rows ordered by first-seen merchant id after identical duplicates are removed.
- Load `processing_fee_percent`, `fixed_fee_cents`, `dispute_fee_cents`, `reserve_percent`, and `minimum_payout_cents` from `data/payout-rules.json` at runtime (no hardcoded values) — changing the rules file must change output without a code change.
- Per-merchant accumulation, in event order:
  - `charge`: `gross_charge_cents += amount_cents`; `processing_fee_cents += Math.round(amount_cents * processing_fee_percent / 100) + fixed_fee_cents`.
  - `refund`: `refund_cents += amount_cents` (does not reverse processing fees).
  - `dispute`: `dispute_cents += amount_cents`; `dispute_fee_cents += dispute_fee_cents` (configured constant, once per dispute event).
- Per-merchant final computation:
  - `net_before_reserve = gross_charge_cents - refund_cents - dispute_cents - processing_fee_cents - dispute_fee_cents`.
  - `reserve_cents = Math.round(net_before_reserve * reserve_percent / 100)` when `net_before_reserve > 0`, else `0`.
  - `payout_cents = net_before_reserve - reserve_cents`.
  - If `0 < payout_cents < minimum_payout_cents`: add that original positive `payout_cents` into `reserve_cents`, then set `payout_cents = 0`; keep the merchant row.
- Successful stdout: exactly one JSON object with only keys `total_payout_cents`, `total_processing_fee_cents`, `total_dispute_fee_cents`, `total_reserve_cents`, `merchants` — no stderr output. Each merchant row has exactly `merchant_id`, `gross_charge_cents`, `refund_cents`, `dispute_cents`, `processing_fee_cents`, `dispute_fee_cents`, `reserve_cents`, `payout_cents`. Each top-level total is the sum of the corresponding final merchant field. All public amounts are integer cents.
- Update `tests/cli.test.js`: keep existing `hello`/`version` tests passing, add at least two new tests for `payout` — one successful payout, one validation failure (non-zero exit, stderr JSON error, no stdout).

## Constraints

- Only touch `bin/cli.js` and `tests/cli.test.js`. Do not touch `server/` or `web/` files, and do not modify `data/payout-rules.json`.
- No new dependencies (package.json currently lists only `express` as a runtime dep for the server; the CLI itself uses only `fs`/`path`).
- Match existing CLI conventions in `bin/cli.js`: `USAGE` text block, `switch` on command, `process.exit` codes, `console.error`/`process.stderr.write` for errors.
- Match existing test conventions in `tests/cli.test.js`: `node:test` + `node:assert` + `execFileSync`, one `test()` block per case.

## Out of Scope

- Any change to `server/` or `web/`.
- Any change to `data/payout-rules.json` contents.
- Any new CLI commands beyond `payout`.
- Adding a `scripts/lint-json.js` or fixing the pre-existing missing `lint:json` package.json script target.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "expect_exit": 0 }
  ]
}
```
