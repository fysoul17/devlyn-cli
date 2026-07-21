<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — edit — add a `payout` case to the existing `switch (command)` (bin/cli.js:46-60) that: parses `--input <path>` the same way `parseNameFlag` parses `--name` (bin/cli.js:27-36); reads and `JSON.parse`s the events file and `data/payout-rules.json` at runtime via `fs`/`path` (Requirement 1 — rule values must never be hardcoded); runs a pre-pass over `events` to dedupe by `id` and detect conflicting duplicates, aborting with exit `2` / stderr-only JSON before any accumulation (Requirement 2); performs the per-merchant integer-cents accumulation exactly as specified (Requirement 3); and either writes the single stdout JSON object (Requirement 4) or, on any validation failure, writes exactly one JSON error object to stderr and exits `2` with nothing on stdout (Requirement 5).
- `tests/cli.test.js` — edit — add `node:test` cases (same `run()`/`execFileSync` harness as tests/cli.test.js:8-10) covering: a successful multi-merchant payout with known-good math against the current `data/payout-rules.json` values (Requirement 3–4); idempotent dedup of a byte-identical duplicate `id` (Requirement 2); a conflicting duplicate `id` aborting with exit `2`, empty stdout, and the exact `{"error":"conflicting_duplicate","id":...}` stderr shape (Requirement 2); and one case per validation failure in Requirement 5 (unknown `type`, missing `merchant_id`, missing `id`, non-positive/non-integer `amount_cents`, missing `events`, invalid input JSON, unreadable input file) each asserting exit `2` and empty stdout. The existing `hello default`, `hello with --name`, and `version prints package version` tests (tests/cli.test.js:12-25) are left byte-for-byte unmodified.

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

**Out-of-scope expansions to refuse:**
- Touching anything under `server/` or `web/` — explicitly forbidden by the Constraints section even though a real payout feature would eventually surface through the HTTP app or frontend.
- Adding any npm dependency (e.g. a JSON-schema validator, a currency/decimal library, an argument-parsing library) — Constraints forbid new `package.json` entries; the existing file already does its own manual flag parsing and JSON validation.
- Adding new commands, flags, currency formatting, persistence, or network calls — explicitly Out of Scope.
- Refactoring `hello`/`version`/`--help` or the `switch` structure "while here" — not requested; only a new `case 'payout'` arm is authorized.

**Ambiguous spec sections to interpret strictly:**
- *"byte-identical JSON content"* for dedup: since the whole input file is parsed once with `JSON.parse`, the per-event original source bytes are not separately retained. The strict, deterministic proxy is `JSON.stringify(event)` equality between the first-seen occurrence and any later occurrence of the same `id` (key insertion order is preserved by `JSON.parse`, so this only matches when the two occurrences are genuinely identical in content and key order). This is documented here rather than silently assumed, since a raw-substring comparison was the alternative and is unnecessary complexity for the stated contract.
- *Validation ordering / "checked before any totals are printed"*: read as a full validate-then-dedupe pass over every event (structural checks: `id`, `merchant_id`, known `type`, integer positive `amount_cents`) completed — and any failure reported — strictly before any accumulation or stdout write begins. No JSON is ever partially written to stdout on a later-discovered error.
- *Missing/absent `--input` flag itself*: not explicitly listed among Requirement 5's validation failures (which enumerate file-content problems). Since `payout --input <path>` is the command's only supported form and an absent path is functionally "cannot read the input file," this is treated the same as the listed "unreadable input file" case — exit `2` with a JSON error on stderr — for contract consistency with the rest of `payout`'s own error handling, rather than falling back to the generic `process.exit(1)` + usage-text pattern used by `hello`'s `--name` flag.
- *Merchant row ordering*: "first-seen event" is evaluated post-dedup, using a `Map` keyed by `merchant_id` populated in event-array iteration order, so a merchant's row position reflects its first surviving (non-duplicate) event.

**Known failure modes for this language/framework:**
- `JSON.parse` throws `SyntaxError` on malformed input JSON or a malformed `--input` file — must be caught and converted to the exit-2 JSON stderr contract, never left as an uncaught exception/stack trace (Requirement 5's "never a silent catch or an uncaught stack trace" — meaning the catch must produce the specified JSON error, not swallow it silently).
- `fs.readFileSync` throws (e.g. `ENOENT`) on a missing/unreadable input path — same catch-and-report requirement, not a bare crash.
- Floating-point drift in `amount_cents * processing_fee_percent / 100` and `net_before_reserve * reserve_percent / 100` — the spec's formulas already specify `Math.round(...)` at each step; implement exactly that arithmetic in the order given rather than introducing a "safer" bignum/decimal workaround, since the spec is prescriptive about the formula, not just the outcome.
- Naming collision: the rules file's `dispute_fee_cents` (a flat per-dispute-event fee configured in `data/payout-rules.json`) and each merchant row's output field of the same name (`dispute_fee_cents`, an accumulated total) are distinct values with the same key name — risk of accidentally aliasing the config variable with the accumulator variable; keep them as clearly distinct local bindings (e.g. `rules.dispute_fee_cents` vs. `merchant.dispute_fee_cents`).
- The `payout_cents < minimum_payout_cents` fold-into-reserve step only applies when `0 < payout_cents`; a `payout_cents` that is already `<= 0` must be left untouched (not folded, not clamped) per the literal Requirement 3 conditional.

## Acceptance restatement

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
