# Generated criteria (free-form, large)

recommend: /devlyn:ideate first — this goal has >10 field/path signals (JSON key names, rule fields, CLI shape) so the classifier routed it through the large-mode best-effort synthesis path instead of trivial/medium. The goal text itself is already close to spec-quality (exact field names, exact formulas, exact error contract for one error class), so the `## Assumptions` below are narrow and should be quick for the user to confirm or correct.

## Requirements

- Add a `payout` subcommand to `bin/cli.js`: `bench-cli payout --input <path>`.
- Read and JSON-parse the file at `<path>` as `{ "events": [...] }`; each event requires `id` (string), `merchant_id` (string), `type` (one of `"charge" | "refund" | "dispute"`), `amount_cents` (positive integer).
- Load `processing_fee_percent`, `fixed_fee_cents`, `dispute_fee_cents`, `reserve_percent`, `minimum_payout_cents` from `data/payout-rules.json` at runtime; do not hardcode these values — editing only the rules file must change the output.
- Idempotency: events sharing an `id` with identical JSON content are applied once. An `id` reused with different content is a "conflicting duplicate": exit `2`, no stdout, and stderr is exactly `{"error":"conflicting_duplicate","id":"<id>"}`, before any totals are computed.
- Merchant rows are ordered by first appearance in the deduplicated event stream (identical duplicates removed first).
- Per event `charge` → adds to `gross_charge_cents` and adds `Math.round(amount_cents * processing_fee_percent / 100) + fixed_fee_cents` to `processing_fee_cents`. `refund` → adds to `refund_cents` only (does not reverse processing fees). `dispute` → adds to `dispute_cents` and adds one `dispute_fee_cents` (rules value) to the merchant's `dispute_fee_cents`.
- Per merchant, derive `net_before_reserve = gross_charge_cents - refund_cents - dispute_cents - processing_fee_cents - dispute_fee_cents`; `reserve_cents = Math.round(net_before_reserve * reserve_percent / 100)` when `net_before_reserve` is positive, else `0`; `payout_cents = net_before_reserve - reserve_cents`.
- Minimum-payout folding: when `0 < payout_cents < minimum_payout_cents`, add that payout amount into `reserve_cents` and set `payout_cents` to `0`, keeping the merchant row.
- On success, stdout is exactly one JSON object with only the keys `total_payout_cents`, `total_processing_fee_cents`, `total_dispute_fee_cents`, `total_reserve_cents`, `merchants`; each merchant row has exactly `merchant_id`, `gross_charge_cents`, `refund_cents`, `dispute_cents`, `processing_fee_cents`, `dispute_fee_cents`, `reserve_cents`, `payout_cents`; each total equals the sum of the corresponding final merchant field; nothing is written to stderr.
- Any of: unknown event `type`, missing `merchant_id`, missing `id`, non-positive or non-integer `amount_cents`, missing `events`, invalid JSON, or an unreadable input path → exit `2`, exactly one JSON error object on stderr, nothing on stdout. JSON-parse and file-read failures must be caught and surfaced through this same JSON error contract, never an uncaught exception / silent catch.
- `tests/cli.test.js`: existing `hello` / `version` tests keep passing; add at least two new tests for `payout` — one successful payout, one validation failure.
- Touch only `bin/cli.js` and `tests/cli.test.js`. No new dependencies. No changes to `server/` or `web/`.

## Out of Scope

- `server/` and `web/` directories, and any other file not listed above.
- New CLI flags beyond `--input`, or changes to the shape of `data/payout-rules.json`.
- Persisting, logging, or writing events anywhere beyond the single stdout/stderr contract described above.

## Assumptions

The goal is unusually precise (exact field names, exact arithmetic, exact error shape for the conflicting-duplicate case), so these are the only real gaps. Each is scope-narrowing and reversible:

- Non-conflicting-duplicate error objects (unknown type, missing field, invalid amount, missing `events`, invalid/unreadable input) have no literal shape specified beyond "exactly one JSON object" — only `conflicting_duplicate` gets an exact shape in the goal. Assumed: `{"error": "<snake_case_code>"}`, optionally with minimal identifying context (e.g. an `id` or index) when one is available.
- "Identical JSON content" for idempotency means deep/structural equality of the parsed event object, not raw byte/whitespace equality of the source text.
- Validation and duplicate-conflict detection process events in file order and fail fast on the first offending event; no partial output is ever produced.
- A missing `--input` flag, a nonexistent path, and a permission-denied path are all treated as the "unreadable input" error class.
- An empty `events` array is valid input (distinct from a missing `events` key) and produces zero merchant rows with all totals `0`.

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
