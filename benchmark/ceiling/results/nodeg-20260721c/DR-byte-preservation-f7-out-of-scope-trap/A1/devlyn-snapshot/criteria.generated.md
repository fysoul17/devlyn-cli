# Generated criteria — --format json for `version` subcommand

## Requirements

- `bench-cli version` (no `--format` flag) keeps printing the bare version string exactly as today — unchanged behavior.
- `bench-cli version --format json` prints valid single-line JSON `{"version":"<x.y.z>"}` matching the version in `package.json`.
- `bench-cli version --format yaml` (or any other unsupported `--format` value) exits with code 1 and prints an error.
- Existing tests in `tests/cli.test.js` continue to pass, plus at least one new test exercises the `--format json` path.

## Constraints

- Touch only `bin/cli.js` and `tests/cli.test.js`. No other subcommands (`hello`, `--help`) or files change.
- No new npm dependencies — use the built-in `JSON.stringify`/`JSON.parse`.
- Code unrelated to the `version --format` feature (including comments and formatting, e.g. the existing `TODO(devlyn)` comment and `parseGreetingFormat` helper) must remain byte-for-byte as-is.
- `tests/cli.test.js`'s `run()` helper uses `execFileSync`, which throws on non-zero exit — the new error-path test must account for that (e.g. catch the thrown error, or use a non-throwing exec helper) rather than assuming a clean return.

## Out of Scope

- `hello` subcommand behavior or its `parseGreetingFormat`/`parseNameFlag` helpers.
- Removing pre-existing dead code (e.g. the unused `parseGreetingFormat`) — not requested, out of scope per Goal-locked execution.
- Any refactor of `main()`'s command dispatch beyond what `--format` parsing requires.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "npm test", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\"0.1.0\"}"] },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1 }
  ]
}
```
