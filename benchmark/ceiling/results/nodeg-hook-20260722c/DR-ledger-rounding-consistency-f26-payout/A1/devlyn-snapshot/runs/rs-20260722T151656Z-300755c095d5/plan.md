# Plan — `bench-cli payout` subcommand

<!-- devlyn:authorized-surface -->
## 1. Files to touch

- `bin/cli.js` — edit — implement the `payout` subcommand: arg parsing (`--input <path>`), rules loading from `data/payout-rules.json`, input read/parse/validate, idempotent dedup + `conflicting_duplicate` detection, per-merchant accumulation and final computation, single-line JSON stdout on success / single-line JSON error on stderr with `exit(2)` on failure. Satisfies Requirements bullets 1–9 and 12–21 of `.devlyn/criteria.generated.md` (`bench-cli payout --input <path>` subcommand, validation contract, idempotency, rule loading, accumulation/final math, stdout shape). Also extend `USAGE` (bin/cli.js:8-19) with the new command and add a `case 'payout':` arm to the existing `switch` (bin/cli.js:46-60).
- `tests/cli.test.js` — edit — add ≥2 new `test()` blocks for `payout` (one successful payout producing the expected totals JSON, one validation failure asserting exit code 2, stderr JSON error object, empty stdout), reusing the existing `run()`/`execFileSync` + `node:test`/`node:assert` conventions (tests/cli.test.js:1-25). Fixture ledger JSON is written to a temp file at test time (`fs.mkdtempSync`/`os.tmpdir()`) inside the test file itself — no new fixture files are added, keeping the touched-file set to exactly these two paths. Satisfies the final Requirements bullet ("Update `tests/cli.test.js`... add at least two new tests for `payout`").

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## 2. Risks

**Out-of-scope expansions to refuse** (per `.devlyn/criteria.generated.md` Out of Scope + Constraints):
- No edits to `data/payout-rules.json`, `server/`, or `web/`.
- No new CLI commands beyond `payout`.
- No `scripts/lint-json.js` or `lint:json` package.json fix — pre-existing gap, not in scope.
- No new runtime dependencies; use only `fs`/`path` (+ `os` in the test file for temp fixtures), matching the existing `bin/cli.js` requires (bin/cli.js:5-6) and `tests/cli.test.js` requires (tests/cli.test.js:1-4).

**Ambiguous spec sections — interpreted strictly, documented here so IMPLEMENT and VERIFY apply the same reading:**
1. The criteria give a literal stderr shape only for `conflicting_duplicate`: `{ "error": "conflicting_duplicate", "id": string }` (criteria line 9). For the other listed failures (unknown `type`, missing `merchant_id`/`id`, invalid `amount_cents`, missing `events`, invalid JSON, unreadable input file) no literal shape is mandated — only "exactly one JSON error object to stderr" + exit 2 + no stdout. Plan: use a consistent `{ "error": "<code>", ...minimal context }` shape for all of them (e.g. `invalid_json`, `unreadable_input`, `missing_events`, `invalid_event` with an `index`/`field`), emitted through one shared helper so every failure path is provably single-object/single-line. New tests will assert on exit code, stderr being a single parseable JSON object with an `error` key, and empty stdout — not on a specific literal string — since the spec does not mandate one beyond `conflicting_duplicate`.
2. "missing `merchant_id`" / "missing `id`" is read as `typeof event.<field> !== 'string'` (covers `undefined`/`null`/wrong type). Empty-string values are not special-cased since the spec only says "missing," not "missing or empty" — adding that check would be unrequested extra validation.
3. "identical JSON content" for dedup is compared field-by-field on the four defined event keys (`id`, `merchant_id`, `type`, `amount_cents`), not raw serialized-text equality — avoids spurious `conflicting_duplicate` flags from harmless key-order differences while still matching "identical content" for this fixed, closed shape.
4. A missing `--input` value (flag omitted or given with no path) is folded into the same "unreadable input file" error family/exit-2 contract rather than left to crash with a raw Node exception — this keeps the "exactly one JSON error, no stdout" guarantee total across every input-acquisition failure without inventing new spec behavior.
5. Reading `data/payout-rules.json` itself has no error contract in Requirements (unlike the `--input` file) and the file is out of scope to modify or mock; a read/parse failure there is left to surface as an ordinary thrown exception (Node's default non-zero exit) rather than adding an unspecified, untestable JSON-error path for a file guaranteed present and valid — no silent catch/fallback either way.

**Known failure modes for this shape of logic:**
- Reserve/minimum-payout adjustment (criteria line 20) must add the *original* positive `payout_cents` into `reserve_cents` before zeroing `payout_cents` — computing in the wrong order double-counts or drops cents.
- All rounding must use `Math.round` exactly where the spec specifies it (processing fee, reserve) — no `Math.floor`/`Math.ceil` substitution, since that would silently diverge from the literal formulas in criteria lines 13 and 18.
- `conflicting_duplicate` must be detected and reported before any totals/stdout are printed (criteria line 9) — implies a full validate-then-dedupe pass over all events before accumulation starts, so a conflict discovered on event N doesn't leave partial output already written.
- Must not regress the two existing tests (`hello`, `version`) — only additive changes to `USAGE` and the `switch`; `parseNameFlag`/`readPackageVersion` stay untouched.

## 3. Acceptance restatement

Verbatim copy of the Requirements section from `.devlyn/criteria.generated.md`:

> - Add a `payout` subcommand to `bin/cli.js`: `bench-cli payout --input <path>`, reading ledger events from the JSON file at `<path>` and printing merchant payout totals to stdout.
> - Input shape: `{ "events": [{ "id": string, "merchant_id": string, "type": "charge" | "refund" | "dispute", "amount_cents": number }] }`. Validate every event; on an unknown `type`, missing `merchant_id`, missing `id`, non-positive or non-integer `amount_cents`, missing `events`, invalid JSON, or an unreadable input file, exit `2`, write exactly one JSON error object to stderr, and write nothing to stdout. Parsing/file-read failures must surface as JSON errors, not silent catches.
> - Idempotency: events with the same `id` and identical JSON content are deduplicated and applied once. The same `id` with differing JSON content is a `conflicting_duplicate` — exit `2`, no stdout, stderr exactly `{ "error": "conflicting_duplicate", "id": string }`, checked before any totals are printed.
> - Merchant ordering: rows ordered by first-seen merchant id after identical duplicates are removed.
> - Load `processing_fee_percent`, `fixed_fee_cents`, `dispute_fee_cents`, `reserve_percent`, and `minimum_payout_cents` from `data/payout-rules.json` at runtime (no hardcoded values) — changing the rules file must change output without a code change.
> - Per-merchant accumulation, in event order:
>   - `charge`: `gross_charge_cents += amount_cents`; `processing_fee_cents += Math.round(amount_cents * processing_fee_percent / 100) + fixed_fee_cents`.
>   - `refund`: `refund_cents += amount_cents` (does not reverse processing fees).
>   - `dispute`: `dispute_cents += amount_cents`; `dispute_fee_cents += dispute_fee_cents` (configured constant, once per dispute event).
> - Per-merchant final computation:
>   - `net_before_reserve = gross_charge_cents - refund_cents - dispute_cents - processing_fee_cents - dispute_fee_cents`.
>   - `reserve_cents = Math.round(net_before_reserve * reserve_percent / 100)` when `net_before_reserve > 0`, else `0`.
>   - `payout_cents = net_before_reserve - reserve_cents`.
>   - If `0 < payout_cents < minimum_payout_cents`: add that original positive `payout_cents` into `reserve_cents`, then set `payout_cents = 0`; keep the merchant row.
> - Successful stdout: exactly one JSON object with only keys `total_payout_cents`, `total_processing_fee_cents`, `total_dispute_fee_cents`, `total_reserve_cents`, `merchants` — no stderr output. Each merchant row has exactly `merchant_id`, `gross_charge_cents`, `refund_cents`, `dispute_cents`, `processing_fee_cents`, `dispute_fee_cents`, `reserve_cents`, `payout_cents`. Each top-level total is the sum of the corresponding final merchant field. All public amounts are integer cents.
> - Update `tests/cli.test.js`: keep existing `hello`/`version` tests passing, add at least two new tests for `payout` — one successful payout, one validation failure (non-zero exit, stderr JSON error, no stdout).
