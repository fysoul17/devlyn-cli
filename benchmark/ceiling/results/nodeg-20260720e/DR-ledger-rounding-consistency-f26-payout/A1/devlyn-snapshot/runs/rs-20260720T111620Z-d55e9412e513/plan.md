# Plan — `bench-cli payout --input <path>`

<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — **edit**. Add a `payout` case to the command `switch` (bin/cli.js:46-60), following the existing dispatch pattern (`hello`/`version` cases, bin/cli.js:47-55) and the existing flag-parsing pattern (`parseNameFlag`, bin/cli.js:27-36). Implements: subcommand + `--input` flag (criteria.generated.md:7); read/validate ledger JSON (criteria.generated.md:8); load payout rules from `data/payout-rules.json` at runtime, never hardcoded (criteria.generated.md:9); idempotent dedupe / conflicting-duplicate detection (criteria.generated.md:10); first-appearance merchant ordering (criteria.generated.md:11); per-event accumulation rules for charge/refund/dispute (criteria.generated.md:12); reserve/payout derivation (criteria.generated.md:13); minimum-payout folding (criteria.generated.md:14); exact success JSON shape on stdout (criteria.generated.md:15); exact JSON-error-on-stderr/exit-2/empty-stdout contract for every validation failure class (criteria.generated.md:16). Also add one line to the existing `USAGE` string (bin/cli.js:8-19) documenting `payout --input <path>`, matching the existing convention that every command is listed there.
- `tests/cli.test.js` — **edit**. Add at least two `test(...)` blocks using the existing `run()`/`execFileSync` harness (tests/cli.test.js:1-10): one successful payout (assert exit 0, empty stderr, exact/derived stdout JSON), one validation failure (assert exit 2, empty stdout, JSON error object on stderr). Keep the three existing `hello`/`version` tests (tests/cli.test.js:12-25) unmodified. Implements: criteria.generated.md:17.

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Scope fence**: `server/`, `web/`, `scripts/lint-json.js`, `package.json`, and `data/payout-rules.json` are out of scope and must not be touched (criteria.generated.md:22-24). No new dependencies — implement everything with Node core modules already available (`fs`, `path`, plus `node:util`).
- **Idempotency comparison must be structural, not textual.** "Identical JSON content" means deep/structural equality of the *parsed* event object, not raw source-text equality (criteria.generated.md:31). A raw `JSON.stringify(a) === JSON.stringify(b)` comparison is key-order-sensitive and would misclassify two structurally-identical events written with keys in a different order as a conflicting duplicate. Use the Node core primitive `require('node:util').isDeepStrictEqual(a, b)` instead — this is the standard-library tool for this exact job (contract rule 5: use standard primitives, don't hand-roll).
- **Rules must be read from `data/payout-rules.json` at runtime on every invocation** (criteria.generated.md:9) — no caching across calls, no inlined numbers; editing only the rules file must change the output. This file is a repo-shipped fixture, not user input — a failure to read/parse it is **not** part of the `--input` validation-error contract and must not be wrapped in the same catch as the ledger-file read (spec's "file-read failures must be caught" language (criteria.generated.md:16) targets the user's `--input` path, not this internal fixture).
- **No partial output.** Validation and duplicate-conflict detection proceed in file order and fail fast on the first offending event (criteria.generated.md:16, :32) — the full result object must be built in memory and `console.log`'d exactly once, only after every event has validated and deduped cleanly. Never write to stdout before validation is fully complete.
- **Duplicate check depends on `id` existing.** Per event, validate required shape (`id` string, `merchant_id` string, `type` ∈ {charge,refund,dispute}, `amount_cents` positive integer) before/alongside the idempotency check, in file order, so the first offending event (whichever kind) is the one reported.
- **Error class collapsing**: missing `--input` flag, a nonexistent path, and a permission-denied path are all the same "unreadable input" error class (criteria.generated.md:33) — do not invent distinct codes for these three.
- **Unspecified error shape**: only `conflicting_duplicate` has a literal required shape — exactly `{"error":"conflicting_duplicate","id":"<id>"}` (criteria.generated.md:10). Every other failure only needs to be "exactly one JSON object" on stderr; plan assumes `{"error":"<snake_case_code>"}`, optionally with an `id` when one is available (criteria.generated.md:30). Do not add extra required keys beyond what verification checks (verification test 3 only asserts `typeof errObj.error === 'string'`).
- **Empty `events: []` is valid**, distinct from a missing `events` key — must succeed with zero merchant rows and every total `0` (criteria.generated.md:34); do not treat it as an error.
- **`refund` never reverses processing fees** — refunds only add to `refund_cents` (criteria.generated.md:12). Resist netting refunds against `processing_fee_cents`.
- **`dispute_fee_cents` is a flat per-event add** from `rules.dispute_fee_cents`, not a percentage of the disputed amount (criteria.generated.md:12).
- **Arithmetic must match exactly**: `processing_fee_cents += Math.round(amount_cents * processing_fee_percent / 100) + fixed_fee_cents`; `net_before_reserve = gross_charge_cents - refund_cents - dispute_cents - processing_fee_cents - dispute_fee_cents`; `reserve_cents = Math.round(net_before_reserve * reserve_percent / 100)` only when `net_before_reserve > 0`, else `0` (never negative); `payout_cents = net_before_reserve - reserve_cents` (criteria.generated.md:12-13).
- **Minimum-payout folding** applies only when `0 < payout_cents < minimum_payout_cents`: fold that payout into `reserve_cents`, set `payout_cents` to `0`, and keep the merchant row regardless (criteria.generated.md:14). A payout of exactly `0` or already negative must not trigger folding (folding a negative value into reserve would be wrong; `0 < payout_cents` guards this).
- **Do not alter existing `hello`/`version` behavior**, the `switch` dispatch structure, or existing tests — only add to them (criteria.generated.md:17).
- **No new CLI flags beyond `--input`** and no changes to the shape of `data/payout-rules.json` (criteria.generated.md:23).

## Acceptance restatement

Verbatim from `.devlyn/criteria.generated.md` (lines 37-63):

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "npm test",
      "exit_code": 0
    },
    {
      "cmd": "node -e \"\nconst fs = require('fs');\nconst { spawnSync } = require('child_process');\nconst assert = require('assert');\nconst rules = JSON.parse(fs.readFileSync('data/payout-rules.json', 'utf8'));\nconst events = [\n  { id: 'c1', merchant_id: 'm1', type: 'charge', amount_cents: 100000 },\n  { id: 'c1', merchant_id: 'm1', type: 'charge', amount_cents: 100000 },\n  { id: 'r1', merchant_id: 'm1', type: 'refund', amount_cents: 5000 },\n  { id: 'd1', merchant_id: 'm1', type: 'dispute', amount_cents: 20000 },\n  { id: 'c2', merchant_id: 'm2', type: 'charge', amount_cents: 1000 },\n];\nfs.writeFileSync('/tmp/devlyn-payout-success.json', JSON.stringify({ events }));\nconst seen = new Map();\nconst order = [];\nconst rows = new Map();\nfor (const ev of events) {\n  const content = JSON.stringify(ev);\n  if (seen.has(ev.id)) {\n    if (seen.get(ev.id) !== content) throw new Error('fixture has an unintended conflicting duplicate');\n    continue;\n  }\n  seen.set(ev.id, content);\n  if (!rows.has(ev.merchant_id)) {\n    rows.set(ev.merchant_id, { merchant_id: ev.merchant_id, gross_charge_cents: 0, refund_cents: 0, dispute_cents: 0, processing_fee_cents: 0, dispute_fee_cents: 0 });\n    order.push(ev.merchant_id);\n  }\n  const row = rows.get(ev.merchant_id);\n  if (ev.type === 'charge') {\n    row.gross_charge_cents += ev.amount_cents;\n    row.processing_fee_cents += Math.round(ev.amount_cents * rules.processing_fee_percent / 100) + rules.fixed_fee_cents;\n  } else if (ev.type === 'refund') {\n    row.refund_cents += ev.amount_cents;\n  } else if (ev.type === 'dispute') {\n    row.dispute_cents += ev.amount_cents;\n    row.dispute_fee_cents += rules.dispute_fee_cents;\n  }\n}\nconst merchants = order.map((mid) => {\n  const row = rows.get(mid);\n  const netBeforeReserve = row.gross_charge_cents - row.refund_cents - row.dispute_cents - row.processing_fee_cents - row.dispute_fee_cents;\n  let reserve = netBeforeReserve > 0 ? Math.round(netBeforeReserve * rules.reserve_percent / 100) : 0;\n  let payout = netBeforeReserve - reserve;\n  if (payout > 0 && payout < rules.minimum_payout_cents) {\n    reserve += payout;\n    payout = 0;\n  }\n  return { merchant_id: row.merchant_id, gross_charge_cents: row.gross_charge_cents, refund_cents: row.refund_cents, dispute_cents: row.dispute_cents, processing_fee_cents: row.processing_fee_cents, dispute_fee_cents: row.dispute_fee_cents, reserve_cents: reserve, payout_cents: payout };\n});\nconst expected = {\n  total_payout_cents: merchants.reduce((s, m) => s + m.payout_cents, 0),\n  total_processing_fee_cents: merchants.reduce((s, m) => s + m.processing_fee_cents, 0),\n  total_dispute_fee_cents: merchants.reduce((s, m) => s + m.dispute_fee_cents, 0),\n  total_reserve_cents: merchants.reduce((s, m) => s + m.reserve_cents, 0),\n  merchants,\n};\nconst res = spawnSync('node', ['bin/cli.js', 'payout', '--input', '/tmp/devlyn-payout-success.json'], { encoding: 'utf8' });\nassert.strictEqual(res.status, 0, 'expected exit 0, got ' + res.status + ' stderr=' + res.stderr);\nassert.strictEqual(res.stderr, '', 'expected no stderr, got ' + JSON.stringify(res.stderr));\nconst parsed = JSON.parse(res.stdout);\nassert.deepStrictEqual(parsed, expected);\nconsole.log('SUCCESS_CHECK_OK');\n\"",
      "exit_code": 0,
      "stdout_contains": ["SUCCESS_CHECK_OK"]
    },
    {
      "cmd": "node -e \"\nconst fs = require('fs');\nconst { spawnSync } = require('child_process');\nconst assert = require('assert');\nconst events = [\n  { id: 'c1', merchant_id: 'm1', type: 'charge', amount_cents: 100000 },\n  { id: 'c1', merchant_id: 'm1', type: 'charge', amount_cents: 200000 },\n];\nfs.writeFileSync('/tmp/devlyn-payout-conflict.json', JSON.stringify({ events }));\nconst res = spawnSync('node', ['bin/cli.js', 'payout', '--input', '/tmp/devlyn-payout-conflict.json'], { encoding: 'utf8' });\nassert.strictEqual(res.status, 2, 'expected exit 2, got ' + res.status);\nassert.strictEqual(res.stdout, '', 'expected empty stdout, got ' + JSON.stringify(res.stdout));\nconst errObj = JSON.parse(res.stderr.trim());\nassert.deepStrictEqual(errObj, { error: 'conflicting_duplicate', id: 'c1' });\nconsole.log('CONFLICT_CHECK_OK');\n\"",
      "exit_code": 0,
      "stdout_contains": ["CONFLICT_CHECK_OK"]
    },
    {
      "cmd": "node -e \"\nconst fs = require('fs');\nconst { spawnSync } = require('child_process');\nconst assert = require('assert');\nfs.writeFileSync('/tmp/devlyn-payout-badjson.json', '{not valid json');\nconst res = spawnSync('node', ['bin/cli.js', 'payout', '--input', '/tmp/devlyn-payout-badjson.json'], { encoding: 'utf8' });\nassert.strictEqual(res.status, 2, 'expected exit 2, got ' + res.status);\nassert.strictEqual(res.stdout, '', 'expected empty stdout, got ' + JSON.stringify(res.stdout));\nconst errObj = JSON.parse(res.stderr.trim());\nassert.strictEqual(typeof errObj, 'object');\nassert.strictEqual(typeof errObj.error, 'string');\nconsole.log('INVALID_JSON_CHECK_OK');\n\"",
      "exit_code": 0,
      "stdout_contains": ["INVALID_JSON_CHECK_OK"]
    }
  ]
}
```
</content>
