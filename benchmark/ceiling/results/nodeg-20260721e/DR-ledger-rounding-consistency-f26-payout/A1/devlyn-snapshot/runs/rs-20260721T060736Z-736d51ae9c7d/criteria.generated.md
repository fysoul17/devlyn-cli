# Generated criteria — bench-cli payout command

## Requirements

- Add a `payout --input <path>` subcommand to `bin/cli.js` (`bench-cli payout --input <path>`) that reads a ledger-events JSON file shaped `{ "events": [{ "id": string, "merchant_id": string, "type": "charge" | "refund" | "dispute", "amount_cents": number }] }` and loads fee/reserve rules from `data/payout-rules.json` (`processing_fee_percent`, `fixed_fee_cents`, `dispute_fee_cents`, `reserve_percent`, `minimum_payout_cents`) — changing that file's values must change output without any code change; never hardcode the rule values.
- Idempotent event handling: events sharing an `id` with byte-identical JSON content are deduplicated to one application; an `id` reused with different JSON content is a conflicting duplicate that must abort with exit `2`, no stdout, and exact stderr JSON `{ "error": "conflicting_duplicate", "id": string }` — checked before any totals are printed. After dedup, merchant rows are ordered by each merchant's first-seen event.
- Per-merchant accumulation, in integer cents throughout: `charge` → `gross_charge_cents += amount_cents`, `processing_fee_cents += Math.round(amount_cents * processing_fee_percent / 100) + fixed_fee_cents`; `refund` → `refund_cents += amount_cents` (does not reverse processing fees); `dispute` → `dispute_cents += amount_cents`, `dispute_fee_cents += dispute_fee_cents` (the configured flat fee, once per dispute event). Then `net_before_reserve = gross_charge_cents - refund_cents - dispute_cents - processing_fee_cents - dispute_fee_cents`; `reserve_cents = Math.round(net_before_reserve * reserve_percent / 100)` when `net_before_reserve > 0`, else `0`; `payout_cents = net_before_reserve - reserve_cents`. If `0 < payout_cents < minimum_payout_cents`, keep the row, fold that positive `payout_cents` into `reserve_cents` (add it), and set `payout_cents = 0`.
- Successful stdout is exactly one JSON object with only the keys `total_payout_cents`, `total_processing_fee_cents`, `total_dispute_fee_cents`, `total_reserve_cents`, `merchants` (nothing on stderr); each merchant row has exactly `merchant_id`, `gross_charge_cents`, `refund_cents`, `dispute_cents`, `processing_fee_cents`, `dispute_fee_cents`, `reserve_cents`, `payout_cents`; each top-level total is the sum of the corresponding final per-merchant field.
- Validation failures — unknown event `type`, missing `merchant_id`, missing `id`, non-positive or non-integer `amount_cents`, missing `events`, invalid input JSON, or an unreadable input file — must exit `2`, write exactly one JSON error object to stderr, and write nothing to stdout; parsing/file-read failures must surface as JSON errors, never a silent catch or an uncaught stack trace.

## Constraints

- Only touch `bin/cli.js` and `tests/cli.test.js`. Do not touch `server/` or `web/` files. Do not add dependencies (no new `package.json` entries).
- Existing `hello` / `version` / `--help` behavior and existing tests in `tests/cli.test.js` must keep passing unmodified in behavior.
- `data/payout-rules.json` already exists at the repo root with today's rule values; read it at runtime rather than embedding its values.
- Follow the existing style in `bin/cli.js` (plain Node `fs`/`path`, `switch` on command, `process.exit` for errors) rather than introducing a framework or new abstraction layer.

## Out of Scope

- The `server/` HTTP app and `web/` frontend.
- Any persistence, network calls, or currency formatting beyond integer cents.
- New CLI commands other than `payout`.

<!-- devlyn:verification -->
## Verification

- Idempotent replay: events with the same `id` and identical JSON content are applied only once; the same `id` with different JSON content is a conflicting duplicate.
- Conflicting duplicate contract: a conflicting duplicate `id` must fail before printing totals with exit `2`, no stdout, and the exact stderr object `{ "error": "conflicting_duplicate", "id": string }`.
- All-or-nothing output on any validation failure (unknown event type, missing `merchant_id`, missing `id`, non-positive or non-integer `amount_cents`, missing `events`, invalid JSON, or unreadable input) — even when other events in the same file are individually valid: exit `2`, exactly one JSON error object on stderr, and nothing on stdout; no merchant totals may be partially printed.
- Successful stdout must be exactly one JSON object whose only keys are `total_payout_cents`, `total_processing_fee_cents`, `total_dispute_fee_cents`, `total_reserve_cents`, and `merchants`, with no stderr output.
- Each merchant row has exactly `merchant_id`, `gross_charge_cents`, `refund_cents`, `dispute_cents`, `processing_fee_cents`, `dispute_fee_cents`, `reserve_cents`, and `payout_cents` — no unexpected keys, no missing keys.
- Every public amount is integer cents, and each top-level total is the sum of its corresponding final merchant field.
- Changing `data/payout-rules.json` values (processing fee percent, fixed fee, dispute fee, reserve percent, minimum payout threshold) must change the result without a code change.

```json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "expect_exit": 0 }
  ]
}
```
