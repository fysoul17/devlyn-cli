<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — edit — add a `payout` case to the `switch (command)` in `main()` (`bin/cli.js:46`), plus new helper functions (arg parsing, rules loading, event validation/dedup, per-merchant computation, output). Implements Requirements 1–5 (command surface, idempotency, per-merchant formula, exact output shape, validation-error contract).
- `tests/cli.test.js` — edit — keep the three existing tests (`bin/cli.js:12-25` unchanged in behavior) and add ≥2 new `test(...)` blocks: one successful payout run, one validation failure. Implements Requirement 6 (test coverage) and the `## Verification` mandate that `node --test tests/` passes.

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

**Out-of-scope expansions to refuse:**
- Touching `server/` or `web/` (both exist at repo root, confirmed via `ls`) — refuse even if payout logic seems reusable there.
- Editing `package.json`, `package-lock.json`, or adding any dependency — refuse; use only `fs`, `path`, and `node:test`/`node:child_process`/`node:os` built-ins already available under Node ≥18 (`package.json:20`, current runtime `v20.19.0`).
- Adding flags/subcommands beyond `payout --input <path>` (e.g. `--output`, `--rules`) — refuse; not requested.
- Changing `hello`, `version`, or `--help` behavior (`bin/cli.js:41-60`) — refuse; existing tests at `tests/cli.test.js:12-25` are the contract and must keep passing unmodified in assertion intent.

**Ambiguous spec sections — strict interpretations locked in before IMPLEMENT:**
1. **"Identical JSON content" for idempotency.** The schema has exactly four event fields (`id`, `merchant_id`, `type`, `amount_cents`). Compare those four field values directly (value equality, not raw-string/key-order comparison) between events sharing an `id`. This avoids false "conflicting duplicate" results from harmless key-order differences in the input file and matches the spec's intent ("identical JSON content" describes the event's meaning, not its byte serialization).
2. **Validation order.** Run in this fixed sequence, failing fast on the first violation and never printing partial stdout: (a) file read (`fs.readFileSync`) → (b) `JSON.parse` → (c) top-level shape: `events` must be a present array → (d) per-event structural validation in input order — `id` present → `merchant_id` present → `type` ∈ {`charge`,`refund`,`dispute`} → `amount_cents` is a positive integer (`Number.isInteger(x) && x > 0`) → (e) only after every event passes (d), duplicate-id conflict detection → (f) computation. This is a deliberate, defensible order (spec lists the failure conditions but not their precedence); documented here so IMPLEMENT and any reviewer don't re-litigate it.
3. **Missing/absent `--input` flag or its value.** Not explicitly enumerated in the criteria's failure list, but the repo's error-handling philosophy (`CLAUDE.md`: "no silent fallback... display a clear error state") and the payout contract's blanket "write exactly one JSON error object to stderr, nothing to stdout, exit 2" cover any input-acquisition failure. Treat a missing `--input` flag or missing value the same as unreadable input: one JSON error object to stderr, exit 2. Do **not** reuse `parseNameFlag`'s plain-text `console.error` + `process.exit(1)` pattern (`bin/cli.js:27-36`) — that pattern is `hello`-specific and must not change; payout gets its own arg parsing with its own error contract.
4. **Error object shape for non-`conflicting_duplicate` failures.** The spec fixes the shape only for `conflicting_duplicate` (`{"error": "conflicting_duplicate", "id": string}`). For every other failure (invalid JSON, unreadable file, missing `events`, and each per-event validation case), emit a single flat JSON object whose first key is `"error"` (a short stable string code, e.g. `invalid_json`, `unreadable_input`, `missing_events`, `invalid_event`) plus minimal identifying context (e.g. `id`/`index` when available). The mechanical check only asserts "valid JSON, non-null, non-array object" for these cases, so this shape is a design choice, not a spec requirement — keep it minimal, don't over-specify fields nobody asked for.
5. **Rounding.** Use `Math.round` exactly as the literal formulas specify (`Math.round(amount_cents * processing_fee_percent / 100) + fixed_fee_cents` for processing fee; `Math.round(net_before_reserve * reserve_percent / 100)` for reserve when `net_before_reserve > 0`, else `0`). No alternative rounding (banker's rounding, `Math.floor`, etc.) — verified against the mechanical check's expected numbers (fee 320, reserve 968, payout 8712 for a 10000-cent charge under the current rules file; confirmed by direct computation).
6. **Threshold clamp scope.** `if (0 < payout_cents < minimum_payout_cents)`, keep the merchant row, fold the original positive payout into `reserve_cents`, zero `payout_cents`. This clamp does **not** apply when `payout_cents <= 0` — merchant rows are always kept regardless of payout sign; only the strictly-between-0-and-threshold case triggers the reserve fold.
7. **Rules file location.** Read `data/payout-rules.json` via `path.join(__dirname, '..', 'data', 'payout-rules.json')`, mirroring the existing `readPackageVersion` pattern (`bin/cli.js:21-25`) for path resolution style consistency. Read it fresh on every invocation (no caching/hardcoding) so rule-file edits change output without a code change, per Requirement 1.

**Known failure modes for this language/framework:**
- **`process.exit()` output truncation.** Calling `process.exit(2)` immediately after a synchronous `console.error`/`process.stderr.write` can still race stdout/stderr flushing to a piped consumer (a documented Node.js gotcha, notably affecting non-TTY/piped destinations). Use `process.exitCode = 2; return;` from the payout handler instead of calling `process.exit()` directly, letting Node exit naturally once the process has nothing left to do. (The pre-existing `process.exit(1)` in the unknown-command branch, `bin/cli.js:59`, is out of scope and untouched.)
- **`execFileSync` throws on non-zero exit.** The existing test helper `run()` (`tests/cli.test.js:8-10`) wraps `execFileSync`, which throws an `Error` (populated with `.status`/`.stdout`/`.stderr`) for non-zero exit codes. The new validation-failure test cannot reuse `run()` as-is for its exit-2 assertion; it must either catch that thrown error or use `spawnSync` (also from `node:child_process`, already an implicit transitive availability — no new dependency) which returns `{status, stdout, stderr}` without throwing. Plan: add a `spawnSync` import to `tests/cli.test.js` for the failure-path test only, mirroring the style already used in the criteria's own mechanical verification commands.
- **Temp file lifecycle in tests.** The two new tests need an input JSON file. Use `node:fs` (`writeFileSync`) and `node:os` (`tmpdir`) — both built-in, no new dependency — to create and clean up a temp file per test (write before, `unlinkSync` after, or in a `finally`), keeping tests hermetic and not littering the repo.
- **JSON stdout exactness.** `console.log(JSON.stringify(result))` appends a single trailing newline, which is fine — tests must `.trim()` before `JSON.parse`, matching the mechanical verification commands' own approach (`r.stdout.trim()`).

## Acceptance restatement

<!-- verbatim copy of .devlyn/criteria.generated.md `## Verification` block -->

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
