# Plan — `bench-cli payout --input <path>`

<!-- devlyn:authorized-surface -->
## Files to touch

| Path | Change | Rationale |
|---|---|---|
| `bin/cli.js` | edit | Add a `payout` case to the existing command `switch` (bin/cli.js:46-60), following the pattern already used by `hello`/`version`: a small per-command handler plus a flag parser modeled on `parseNameFlag` (bin/cli.js:27-36). Implements Requirements 1–16 (subcommand entry point, `--input` flag parsing, rules load, idempotent dedup, per-merchant accounting, reserve/clamp math, success stdout shape, validation-error stderr shape). |
| `tests/cli.test.js` | edit | Append new `test(...)` blocks after the existing three (tests/cli.test.js:12-25) — one successful payout run, one validation-failure run — without touching the existing assertions. Implements Requirement 17. |

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

No other path is touched. `data/payout-rules.json` is read at runtime via `fs.readFileSync` + `JSON.parse` (Requirement 3) and is never edited (Out of Scope).

## Risks

**Out-of-scope expansions to refuse:**
- Any edit to `data/payout-rules.json`, `server/`, `web/`, `package.json`, or any new file — Out of Scope is explicit; refuse even if a rules-file tweak would make a test read more cleanly.
- Any new npm dependency (e.g. a deep-equal or JSON-diff package) — Node core already provides `util.isDeepStrictEqual`, so nothing new is needed.
- Any additional subcommand or flag beyond `payout --input <path>` — Out of Scope caps new commands at `payout`.
- Refactoring the existing `hello`/`version` handlers or the `USAGE` string "while we're in the file" — not requested, existing 3 tests are contract and must keep passing unmodified.

**Ambiguous spec sections, resolved per the criteria's own Assumptions (treated as fixed, not re-litigated):**
- *Deep-equal idempotency* — "same `id`, identical JSON content" must be key-reordering-insensitive (Assumption 1), so implementation must NOT compare raw strings; use `require('util').isDeepStrictEqual(parsedA, parsedB)` on the parsed per-event object, keyed by `id`, in first-seen order.
- *Non-integer / non-positive `amount_cents`* — covers `NaN`, `Infinity`, non-number typeof, and fractional values (non-integer); covers `0` and negatives (non-positive) — per Assumption 3. `Number.isInteger(amount_cents) && amount_cents > 0` is the literal test.
- *Empty `events` array* — valid, produces all-zero output; only a *missing* `events` key is a validation error (Assumption 4).
- *Validation order* — array order, first invalid event wins (Assumption 5); dedup and per-event field validation both need to run in a single forward pass over `events`, not two passes, so the *first* problem encountered (whether a field-validation failure or a conflicting duplicate) is the one reported. Field validation (unknown `type`, missing `merchant_id`, missing `id`, bad `amount_cents`) must run before the dedup check for that same event, since dedup needs a valid `id` to key on.
- *Per-event vs per-merchant fee rounding* — Requirement 12's formula (`processing_fee_cents += Math.round(amount_cents * processing_fee_percent / 100) + fixed_fee_cents`) is stated as an accumulator inside the event loop, i.e. rounding happens **per charge event**, then summed — not rounded once on the merchant's aggregate gross. The two only coincide when a merchant has exactly one charge (as in verification commands #2 and #3); with multiple charges per merchant they diverge, so IMPLEMENT must round per event.
- *Error-object shape for non-`conflicting_duplicate` validation failures* — the criteria specifies the literal shape only for `conflicting_duplicate` (`{"error":"conflicting_duplicate","id":"<id>"}`); other validation failures only require "exactly one JSON error object" to stderr with nothing on stdout. IMPLEMENT should pick one consistent minimal shape (e.g. `{"error":"<code>"}`, optionally with the offending `id`/field) — this is an implementation choice within an underspecified but non-contradictory area, not an ambiguity that blocks planning.
- *Verification command #3 says `stdout_contains` for the conflicting-duplicate case* while Requirement 4 explicitly states that case's output goes to **stderr** with **no stdout**. Resolution: implement per the literal Requirement text (stderr-only, exit 2, no stdout) since Assumptions instruct treating Requirements as fixed; the verification harness likely captures combined stdout+stderr under one label. This is flagged, not silently reinterpreted.

**Known failure modes for this language/framework:**
- `fs.readFileSync` throws (`ENOENT`/`EACCES`/etc.) for a missing/unreadable `--input` path — must be caught explicitly and turned into a visible JSON stderr error + exit 2 (per Error Handling Philosophy: explicit catch-and-display, not a silent fallback) — satisfies Requirement 16's "unreadable input file ... surface as JSON errors, never silent catches."
- `JSON.parse` throws `SyntaxError` on malformed `--input` content or malformed `data/payout-rules.json` — same explicit-catch treatment for the input file; `payout-rules.json` is asserted valid by Assumption 6 so no defensive handling is added there (would be unrequested robustness for a file that's Out of Scope to touch or validate).
- Floating-point arithmetic on `amount_cents * processing_fee_percent / 100` and `net_before_reserve * reserve_percent / 100` — follow the spec's literal `Math.round(...)` at each accumulation point; no additional epsilon-correction or currency library, since none is specified and none is needed for the given rule values.
- Merchant insertion order must be preserved via a `Map` (insertion-ordered in JS) keyed by `merchant_id`, populated in first-seen order *after* duplicate removal — a plain object would coincidentally preserve string-key order too, but `Map` is the idiomatic/explicit choice.
- Top-level totals must be a straight sum of the final per-merchant fields (post-clamp) — compute totals in a second pass over the finished merchant array rather than accumulating separately, to guarantee the "each total equals the sum of the corresponding final merchant field" invariant by construction rather than by coincidence.

## Acceptance restatement

Verbatim from `.devlyn/criteria.generated.md`'s `## Verification` block:

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
