# Generated criteria — bench-cli payout command

## Requirements

- Add a `bench-cli payout --input <path>` command that reads `{ "events": [{ "id": string, "merchant_id": string, "type": "charge"|"refund"|"dispute", "amount_cents": number }] }` from the given JSON file and reads processing fee percent, fixed fee, dispute fee, reserve percent, and minimum payout threshold from `data/payout-rules.json` at runtime (no hardcoded rule values — changing the rules file must change the result without a code change).
- Events with the same `id` and identical JSON content are idempotent and applied only once. The same `id` with a different JSON content is a conflicting duplicate: the command must exit `2`, print nothing to stdout, and print exactly the JSON object `{ "error": "conflicting_duplicate", "id": string }` to stderr. Merchant rows are ordered by first-seen merchant after identical duplicates are removed.
- Per-merchant computation: a `charge` increases `gross_charge_cents` and adds `Math.round(amount_cents * processing_fee_percent / 100) + fixed_fee_cents` to `processing_fee_cents`; a `refund` increases `refund_cents` and does not reverse processing fees; a `dispute` increases `dispute_cents` and adds one `dispute_fee_cents`. Then `net_before_reserve = gross_charge_cents - refund_cents - dispute_cents - processing_fee_cents - dispute_fee_cents`; `reserve_cents` is `Math.round(net_before_reserve * reserve_percent / 100)` when that net is positive, else `0`; `payout_cents = net_before_reserve - reserve_cents`. If `0 < payout_cents < minimum_payout_cents`, keep the merchant row, add that original positive payout amount to `reserve_cents`, and set `payout_cents` to `0`.
- Successful stdout is exactly one JSON object with only the keys `total_payout_cents`, `total_processing_fee_cents`, `total_dispute_fee_cents`, `total_reserve_cents`, and `merchants` (no stderr); each merchant row has exactly `merchant_id`, `gross_charge_cents`, `refund_cents`, `dispute_cents`, `processing_fee_cents`, `dispute_fee_cents`, `reserve_cents`, and `payout_cents`; every top-level total is the sum of the corresponding final merchant field; every public amount is integer cents.
- An unknown event `type`, missing `merchant_id`, missing `id`, non-positive or non-integer `amount_cents`, missing `events`, invalid JSON, or unreadable input must exit `2`, write exactly one JSON error object to stderr, and write nothing to stdout — parsing and file-read failures must surface as JSON errors, not silent catches.
- Update `tests/cli.test.js` so the existing `hello`/`version` tests still pass and add at least two new tests for the payout command: one successful payout and one validation failure.

## Constraints

- Only touch `bin/cli.js` and `tests/cli.test.js`; do not touch `server/` or `web/` files.
- Do not add dependencies; use Node's built-ins (`fs`, `path`, `node:test`) consistent with the existing CommonJS `require`-based style in `bin/cli.js` and the `execFileSync`-based style in `tests/cli.test.js`.
- Do not change the behavior of the existing `hello`, `version`, or `--help` commands.

## Out of Scope

- Any change to `server/` or `web/` files.
- New CLI commands or flags beyond `payout --input <path>`.
- Adding or upgrading dependencies, or editing `package.json`.

<!-- devlyn:verification -->
## Verification

- `node --test tests/` passes (includes the two or more new payout tests required above).
- A conflicting duplicate (same `id`, different JSON content) exits `2`, prints nothing to stdout, and prints exactly `{ "error": "conflicting_duplicate", "id": string }` to stderr.
- A validation failure (e.g. a `charge` event missing `merchant_id`) exits `2`, prints nothing to stdout, and prints exactly one JSON error object to stderr.
- A successful single-charge payout run against `data/payout-rules.json`'s current rule values produces exactly the top-level keys `total_payout_cents`, `total_processing_fee_cents`, `total_dispute_fee_cents`, `total_reserve_cents`, `merchants`, with no stderr, and the fee/reserve/payout arithmetic matches the spec's formulas exactly.

```json
{
  "verification_commands": [
    {
      "cmd": "node --test tests/",
      "exit_code": 0
    },
    {
      "cmd": "tmp_in=$(mktemp)\ntmp_check=$(mktemp)\ncat > \"$tmp_in\" <<'EOF_IN'\n{\"events\":[{\"id\":\"c1\",\"merchant_id\":\"m1\",\"type\":\"charge\",\"amount_cents\":10000},{\"id\":\"c1\",\"merchant_id\":\"m1\",\"type\":\"charge\",\"amount_cents\":20000}]}\nEOF_IN\ncat > \"$tmp_check\" <<'EOF_CHECK'\nconst { spawnSync } = require('child_process');\nconst inputPath = process.argv[2];\nconst r = spawnSync('node', ['bin/cli.js', 'payout', '--input', inputPath], { encoding: 'utf8' });\nif (r.status !== 2) { console.error('EXIT_MISMATCH', r.status); process.exit(1); }\nif (r.stdout !== '') { console.error('UNEXPECTED_STDOUT', JSON.stringify(r.stdout)); process.exit(1); }\nlet parsed;\ntry { parsed = JSON.parse(r.stderr.trim()); } catch (e) { console.error('STDERR_NOT_JSON', JSON.stringify(r.stderr)); process.exit(1); }\nconst keys = Object.keys(parsed).sort();\nif (keys.join(',') !== 'error,id') { console.error('KEYS_MISMATCH', keys.join(',')); process.exit(1); }\nif (parsed.error !== 'conflicting_duplicate' || parsed.id !== 'c1') { console.error('VALUE_MISMATCH', JSON.stringify(parsed)); process.exit(1); }\nconsole.log('DUP_CHECK_OK');\nEOF_CHECK\nnode \"$tmp_check\" \"$tmp_in\"\nrc=$?\nrm -f \"$tmp_in\" \"$tmp_check\"\nexit $rc\n",
      "exit_code": 0,
      "stdout_contains": [
        "DUP_CHECK_OK"
      ]
    },
    {
      "cmd": "tmp_in=$(mktemp)\ntmp_check=$(mktemp)\ncat > \"$tmp_in\" <<'EOF_IN'\n{\"events\":[{\"id\":\"e1\",\"type\":\"charge\",\"amount_cents\":100}]}\nEOF_IN\ncat > \"$tmp_check\" <<'EOF_CHECK'\nconst { spawnSync } = require('child_process');\nconst inputPath = process.argv[2];\nconst r = spawnSync('node', ['bin/cli.js', 'payout', '--input', inputPath], { encoding: 'utf8' });\nif (r.status !== 2) { console.error('EXIT_MISMATCH', r.status); process.exit(1); }\nif (r.stdout !== '') { console.error('UNEXPECTED_STDOUT', JSON.stringify(r.stdout)); process.exit(1); }\nlet parsed;\ntry { parsed = JSON.parse(r.stderr.trim()); } catch (e) { console.error('STDERR_NOT_JSON', JSON.stringify(r.stderr)); process.exit(1); }\nif (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) { console.error('STDERR_NOT_OBJECT'); process.exit(1); }\nconsole.log('ERROR_CHECK_OK');\nEOF_CHECK\nnode \"$tmp_check\" \"$tmp_in\"\nrc=$?\nrm -f \"$tmp_in\" \"$tmp_check\"\nexit $rc\n",
      "exit_code": 0,
      "stdout_contains": [
        "ERROR_CHECK_OK"
      ]
    },
    {
      "cmd": "tmp_in=$(mktemp)\ntmp_check=$(mktemp)\ncat > \"$tmp_in\" <<'EOF_IN'\n{\"events\":[{\"id\":\"c1\",\"merchant_id\":\"m1\",\"type\":\"charge\",\"amount_cents\":10000}]}\nEOF_IN\ncat > \"$tmp_check\" <<'EOF_CHECK'\nconst { spawnSync } = require('child_process');\nconst inputPath = process.argv[2];\nconst r = spawnSync('node', ['bin/cli.js', 'payout', '--input', inputPath], { encoding: 'utf8' });\nif (r.status !== 0) { console.error('EXIT_MISMATCH', r.status, r.stderr); process.exit(1); }\nif (r.stderr !== '') { console.error('UNEXPECTED_STDERR', JSON.stringify(r.stderr)); process.exit(1); }\nlet o;\ntry { o = JSON.parse(r.stdout.trim()); } catch (e) { console.error('STDOUT_NOT_JSON', JSON.stringify(r.stdout)); process.exit(1); }\nconst topKeys = Object.keys(o).sort().join(',');\nif (topKeys !== 'merchants,total_dispute_fee_cents,total_payout_cents,total_processing_fee_cents,total_reserve_cents') {\n  console.error('TOP_KEYS_MISMATCH', topKeys); process.exit(1);\n}\nif (o.total_payout_cents !== 8712 || o.total_processing_fee_cents !== 320 || o.total_dispute_fee_cents !== 0 || o.total_reserve_cents !== 968) {\n  console.error('TOTALS_MISMATCH', JSON.stringify(o)); process.exit(1);\n}\nconst m = o.merchants[0];\nconst rowKeys = Object.keys(m).sort().join(',');\nif (rowKeys !== 'dispute_cents,dispute_fee_cents,gross_charge_cents,merchant_id,payout_cents,processing_fee_cents,refund_cents,reserve_cents') {\n  console.error('ROW_KEYS_MISMATCH', rowKeys); process.exit(1);\n}\nif (m.merchant_id !== 'm1' || m.gross_charge_cents !== 10000 || m.processing_fee_cents !== 320 || m.reserve_cents !== 968 || m.payout_cents !== 8712) {\n  console.error('ROW_VALUES_MISMATCH', JSON.stringify(m)); process.exit(1);\n}\nconsole.log('PAYOUT_CHECK_OK');\nEOF_CHECK\nnode \"$tmp_check\" \"$tmp_in\"\nrc=$?\nrm -f \"$tmp_in\" \"$tmp_check\"\nexit $rc\n",
      "exit_code": 0,
      "stdout_contains": [
        "PAYOUT_CHECK_OK"
      ]
    }
  ]
}
```
