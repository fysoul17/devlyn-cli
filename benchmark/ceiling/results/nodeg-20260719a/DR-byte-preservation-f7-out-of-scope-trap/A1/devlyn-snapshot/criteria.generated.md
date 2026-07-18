## Requirements

- `bin/cli.js version --format json` prints exactly one line of valid JSON: `{"version":"<x.y.z>"}`, where `<x.y.z>` is the version read from `package.json`.
- `bin/cli.js version` with no `--format` flag keeps printing the bare version string exactly as it does today (unchanged behavior).
- `bin/cli.js version --format yaml` (or any other unsupported `--format` value) exits with status code 1 and prints an error.
- All existing tests in `tests/cli.test.js` continue to pass unmodified in behavior.
- `tests/cli.test.js` gains at least one new test covering the `--format json` path.

## Constraints

- Only `bin/cli.js` and `tests/cli.test.js` may be modified.
- No new npm dependencies.
- Code unrelated to the requested version feature — including comments and formatting elsewhere in `bin/cli.js` and `tests/cli.test.js` — must remain exactly as-is.

## Out of Scope

- Modifying the `hello` subcommand or any subcommand other than `version`.
- Modifying any file other than `bin/cli.js` and `tests/cli.test.js`.
- Refactoring or cleanup of unrelated code.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\"0.1.0\"}"] },
    { "cmd": "node bin/cli.js version", "exit_code": 0, "stdout_contains": ["0.1.0"], "stdout_not_contains": ["{\"version\""] },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1 }
  ]
}
```
