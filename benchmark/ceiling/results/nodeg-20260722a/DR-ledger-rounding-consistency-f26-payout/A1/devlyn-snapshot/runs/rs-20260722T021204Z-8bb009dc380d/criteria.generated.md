# Generated Criteria — bench-cli payout command

recommend: /devlyn:ideate first (large, best-effort spec synthesized from a detailed free-form goal — review the Assumptions below).

## Requirements

- [ ] Add a `payout` subcommand to `bin/cli.js`, invoked as `bench-cli payout --input <path>` (equivalently `node bin/cli.js payout --input <path>`).
- [ ] Read ledger events from the JSON file at `--input <path>`: `{ "events": [{ "id": string, "merchant_id": string, "type": "charge"|"refund"|"dispute", "amount_cents": number }] }`.
- [ ] Load processing fee percent, fixed fee cents, dispute fee cents, reserve percent, and minimum payout threshold cents from `data/payout-rules.json` at runtime — never hardcoded; a rules-file edit alone must change output.
- [ ] Idempotent handling: events with the same `id` and identical JSON content (deep-equal parsed value) apply only once. The same `id` with differing content is a `conflicting_duplicate` — exit `2`, no stdout, stderr is exactly `{"error":"conflicting_duplicate","id":"<id>"}`.
- [ ] Merchant rows ordered by first-seen merchant id after identical duplicates are removed.
- [ ] Per merchant: `charge` → `gross_charge_cents += amount_cents`; `processing_fee_cents += Math.round(amount_cents * processing_fee_percent / 100) + fixed_fee_cents`. `refund` → `refund_cents += amount_cents` (does not reverse processing fees). `dispute` → `dispute_cents += amount_cents`; `dispute_fee_cents += <configured dispute_fee_cents>`.
- [ ] Compute `net_before_reserve = gross_charge_cents - refund_cents - dispute_cents - processing_fee_cents - dispute_fee_cents`. `reserve_cents = Math.round(net_before_reserve * reserve_percent / 100)` when `net_before_reserve > 0`, else `0`. `payout_cents = net_before_reserve - reserve_cents`.
- [ ] Minimum-payout clamp: if `0 < payout_cents < minimum_payout_cents`, keep the merchant row, add the pre-clamp positive `payout_cents` to `reserve_cents`, and set `payout_cents` to `0`.
- [ ] Successful stdout is exactly one JSON object with only the keys `total_payout_cents`, `total_processing_fee_cents`, `total_dispute_fee_cents`, `total_reserve_cents`, `merchants` — no stderr output. Each merchant row has exactly `merchant_id`, `gross_charge_cents`, `refund_cents`, `dispute_cents`, `processing_fee_cents`, `dispute_fee_cents`, `reserve_cents`, `payout_cents`. Each top-level total equals the sum of the corresponding final merchant field.
- [ ] Validation failures — unknown event `type`, missing `merchant_id`, missing `id`, non-positive or non-integer `amount_cents`, missing `events`, invalid input JSON, or an unreadable input file — exit `2`, write exactly one JSON error object to stderr, write nothing to stdout. Parsing/file-read failures surface as JSON errors, never silent catches.
- [ ] Update `tests/cli.test.js`: existing tests keep passing; add at least two new tests for the payout command — one successful payout, one validation failure.
- [ ] No new dependencies. Only `bin/cli.js` and `tests/cli.test.js` are touched; `server/`, `web/`, and `data/payout-rules.json` are untouched.

## Assumptions

(every assumption below is scope-narrowing and reversible — flag for user review per the Large-branch contract)

- "Identical JSON content" for idempotency means deep-value equality of the parsed event object, not raw-byte string equality, so key reordering alone does not trigger `conflicting_duplicate`.
- JSON emitted to stdout/stderr uses plain `JSON.stringify` (no added whitespace) via `console.log` / `console.error`, matching the existing CLI's plain-output style.
- `amount_cents` "non-integer" covers `NaN`, `Infinity`, non-number types, and fractional values; "non-positive" covers `0` and negative values.
- An `events` array present but empty is valid (produces `merchants: []` and all totals `0`); only a missing `events` key is a validation error.
- Validation runs in array order; the first invalid event encountered is the one reported.
- `data/payout-rules.json` already contains all five required fields and needs no changes for this task.
- `bin/cli.js`'s existing command-dispatch `switch` is extended with a new `payout` case; existing `hello` / `version` / help behavior is unchanged.

## Out of Scope

- Any change to `server/`, `web/`, `data/payout-rules.json`, or files other than `bin/cli.js` and `tests/cli.test.js`.
- New npm dependencies.
- New CLI commands beyond `payout`.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "npm test", "exit_code": 0 },
    {
      "cmd": "printf '%s' '{\"events\":[{\"id\":\"e1\",\"merchant_id\":\"m1\",\"type\":\"charge\",\"amount_cents\":100000}]}' > /tmp/devlyn-payout-ok.json && node bin/cli.js payout --input /tmp/devlyn-payout-ok.json",
      "exit_code": 0,
      "stdout_contains": ["total_payout_cents", "merchants", "m1", "87363", "9707", "2930"]
    },
    {
      "cmd": "printf '%s' '{\"events\":[{\"id\":\"e1\",\"merchant_id\":\"m1\",\"type\":\"charge\",\"amount_cents\":1000}]}' > /tmp/devlyn-payout-min.json && node bin/cli.js payout --input /tmp/devlyn-payout-min.json",
      "exit_code": 0,
      "stdout_contains": ["m1", "941", "59"]
    },
    {
      "cmd": "printf '%s' '{\"events\":[{\"id\":\"e1\",\"merchant_id\":\"m1\",\"type\":\"charge\",\"amount_cents\":100000},{\"id\":\"e1\",\"merchant_id\":\"m1\",\"type\":\"charge\",\"amount_cents\":500}]}' > /tmp/devlyn-payout-dup.json && node bin/cli.js payout --input /tmp/devlyn-payout-dup.json",
      "exit_code": 2,
      "stdout_contains": ["conflicting_duplicate", "e1"]
    },
    {
      "cmd": "printf '%s' '{}' > /tmp/devlyn-payout-bad.json && node bin/cli.js payout --input /tmp/devlyn-payout-bad.json",
      "exit_code": 2
    }
  ]
}
```
