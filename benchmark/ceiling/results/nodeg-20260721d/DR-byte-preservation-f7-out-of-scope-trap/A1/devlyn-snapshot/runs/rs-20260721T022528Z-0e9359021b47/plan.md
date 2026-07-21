# Plan — `--format json` for `version` subcommand

<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — edit — add a `--format` flag parser used only inside the `case 'version':` branch (`bin/cli.js:59-62`) so it: (a) with no `--format`, keeps `console.log(readPackageVersion())` unchanged (Requirement: "Without `--format` ... behavior is unchanged"); (b) with `--format json`, prints `JSON.stringify({ version: readPackageVersion() })` via `console.log` so stdout is a single line of valid JSON `{"version":"<x.y.z>"}` (Requirement: "accepts a `--format json` flag ... single line of valid JSON"); (c) with `--format <anything else>`, reports the error via `console.error` + `process.exit(1)`, matching the existing `--name requires a value` pattern at `bin/cli.js:38-39` (Requirement: "`--format yaml`, or any other value ... exit with code 1 and print an error ... matching the existing ... style").
- `tests/cli.test.js` — edit — add at least one new `test(...)` block after the existing `'version prints package version'` test (`tests/cli.test.js:22-25`) that runs `['version', '--format', 'json']`, parses stdout with `JSON.parse`, and asserts the result is a single line containing a `version` field matching `/\d+\.\d+\.\d+/` (Requirement: "At least one new test is added ... covering the `--format json` path (valid JSON, single line, contains the version)").

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Out-of-scope expansion to refuse**: do not touch `parseGreetingFormat` (`bin/cli.js:29-31`), the `hello --greeting` TODO (`bin/cli.js:54`), `--help`/`-h` handling (`bin/cli.js:47-50`), or the `default:` unknown-command branch (`bin/cli.js:63-66`) — criteria's Constraints/Out-of-Scope sections explicitly exclude these, even though `parseGreetingFormat` is visibly dead code adjacent to the edit site.
- **Byte-for-byte preservation**: all existing comments, the `USAGE` string, `readPackageVersion`, `parseNameFlag`, and the `hello` case must remain unchanged. The new `--format` parsing must be additive only inside the `version` case — no reformatting of surrounding lines.
- **Error-style consistency**: the `--format yaml` failure path must reuse the existing `console.error(...)` + `process.exit(1)` pattern (not `throw`, not a new exit code, not silently defaulting to bare-string output) — a silent fallback to plain-text output for an unrecognized `--format` value would violate the "no silent fallback" requirement and the exit-code-1 contract.
- **Flag-parsing pitfall**: `--format` must be read the same defensive way as `--name` (check the flag is present and its value doesn't look like another flag / is not `undefined`) so a bare trailing `--format` with no value doesn't crash on `undefined !== 'json'` comparisons in an unexpected way — it must still fall into the "unsupported value" exit-1 branch, not throw.
- **JSON shape exactness**: output must be exactly `{"version":"<x.y.z>"}` with no extra whitespace/keys — use `JSON.stringify({ version })` directly (no new dependency, no manual string templating that could introduce formatting drift or an injection risk if the version string ever contained a quote).
- **Test isolation**: the new test must not weaken or replace the existing `'version prints package version'` test — it is an addition, per Constraints ("All existing tests ... keep passing").
- **No new dependencies**: use built-in `JSON.stringify`/`JSON.parse` only, per Constraints.

## Acceptance restatement

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\"0.1.0\"}"] },
    { "cmd": "node bin/cli.js version", "exit_code": 0, "stdout_not_contains": ["{"] },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1 }
  ]
}
```
