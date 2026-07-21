<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — edit — add a `--format` flag to the `version` case (`bin/cli.js:59-62`) plus one new helper function (sibling to `parseNameFlag`, `bin/cli.js:33-42`) that parses `--format`, following the same read-value / `console.error` + `process.exit(1)` pattern. Rationale: Requirements "Add a `--format json` option to the `version` subcommand", "print valid single-line JSON with `--format json`", "keep bare version string without `--format`", and "`--format yaml` (or other unsupported value) exits 1 with an error message".
- `tests/cli.test.js` — edit — add one new `test(...)` block using the existing `run()` helper (`tests/cli.test.js:8-10`) that asserts `run(['version', '--format', 'json'])` produces valid JSON matching `{"version":"<x.y.z>"}`. Rationale: Requirement "Add at least one new test in `tests/cli.test.js` covering the `--format json` path."

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Refuse out-of-scope touches.** Do not modify `hello` (`bin/cli.js:53-58`), the default/`--help` branches, `USAGE` (`bin/cli.js:8-19`), or the unused `parseGreetingFormat` helper and its TODO comment (`bin/cli.js:27-31`) — the criteria explicitly bars this, even though `--format` conceptually resembles `parseGreetingFormat`. Do not add `--format` to the `USAGE` string — the constraint says existing `USAGE` text stays byte-for-byte as-is, and the spec does not ask for a help-text update.
- **No new npm dependencies.** `JSON.stringify({ version: readPackageVersion() })` produces the required single-line `{"version":"<x.y.z>"}` with only built-ins — no JSON/YAML library needed.
- **Ambiguous case: `--format` given with no value or a value starting with `-`.** Not explicitly enumerated in the criteria's happy/error paths. Resolve strictly by mirroring `parseNameFlag`'s existing behavior for the same shape of problem (missing/flag-like value → `console.error` + `process.exit(1)`), rather than inventing a different convention or silently defaulting to plain output.
- **Do not weaken or restructure existing tests.** The three existing `test(...)` blocks in `tests/cli.test.js` (hello default, hello with `--name`, version prints package version) must keep passing unchanged; only append the new test.
- **Known failure mode: `execFileSync` throws on non-zero exit.** The existing `run()` helper (`tests/cli.test.js:8-10`) does not catch child-process errors, so it can only be used directly for the success-path test (`--format json`, exit 0). Do not add a `run()`-based test for the `--format yaml` error path — that would require `try/catch`/`error.status` handling not requested by the criteria (only one new test, covering the json path, is required). The `--format yaml` exit-1 behavior is exercised by the separate `node bin/cli.js version --format yaml` verification command, not by the test file.
- **Match existing style exactly.** New helper function follows `parseNameFlag`'s shape (`argv.indexOf`, guard on missing/flag-like value, `console.error` + `process.exit(1)`); new test follows the existing `test(name, () => { ... })` / `assert.match` idiom already used for `version prints package version` (`tests/cli.test.js:22-25`).

## Acceptance restatement

```json
{
  "verification_commands": [
    { "cmd": "node bin/cli.js version", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1 },
    { "cmd": "node --test tests/cli.test.js", "exit_code": 0 }
  ]
}
```
