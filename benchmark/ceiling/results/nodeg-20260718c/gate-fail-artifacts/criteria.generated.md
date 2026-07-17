# Criteria — add `--format json` to the `version` subcommand

## Requirements

- `bin/cli.js`'s `version` subcommand accepts a `--format json` flag. When present, it prints a single line of valid JSON `{"version":"<x.y.z>"}` (the exact version string from `package.json`) instead of the bare version string.
- Without `--format`, the `version` subcommand's output is unchanged: the bare version string on its own line.
- `--format yaml`, or any `--format` value other than `json`, causes `version` to exit with code 1 and print an error (existing `--name requires a value` error pattern in `bin/cli.js` is the model: `console.error(...)` then `process.exit(1)`).
- All existing tests in `tests/cli.test.js` continue to pass unmodified in behavior.
- At least one new test in `tests/cli.test.js` covers the `--format json` path (asserts the output is valid, single-line JSON with a `version` key matching the package version).

## Constraints

- Only `bin/cli.js` and `tests/cli.test.js` may change.
- No new npm dependencies — use built-in `JSON.stringify`.
- Do not modify the `hello` subcommand, `--help`/`-h`, `USAGE` text, or any other existing behavior.
- Code unrelated to the version/`--format` feature — including existing comments and formatting — must remain byte-for-byte unchanged. No unrelated refactoring or cleanup.

## Out of Scope

- Any subcommand other than `version`.
- Any file other than `bin/cli.js` and `tests/cli.test.js`.
- Adding a `--format` option to any command other than `version`.

<!-- devlyn:verification -->
## Verification

```json
{"verification_commands":[
  {"cmd":"node bin/cli.js version", "exit_code":0, "stdout_contains":["0.1.0"]},
  {"cmd":"node bin/cli.js version --format json", "exit_code":0, "stdout_contains":["{\"version\":\"0.1.0\"}"]},
  {"cmd":"node bin/cli.js version --format yaml", "exit_code":1},
  {"cmd":"npm test", "exit_code":0}
]}
```
