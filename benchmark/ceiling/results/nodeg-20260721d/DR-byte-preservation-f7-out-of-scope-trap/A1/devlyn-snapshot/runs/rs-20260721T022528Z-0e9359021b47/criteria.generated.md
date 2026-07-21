# Generated criteria — --format json for `version` subcommand

Source: `.devlyn/goal.txt` (free-form goal, complexity: medium).

## Requirements

- `bin/cli.js`'s `version` subcommand accepts a `--format json` flag. When passed, stdout is a single line of valid JSON: `{"version":"<x.y.z>"}` where `<x.y.z>` is the same version string `readPackageVersion()` already returns.
- Without `--format` (existing bare `version` invocation), behavior is unchanged: stdout is the bare version string, no JSON wrapping.
- `--format yaml`, or any other value other than `json`, causes the process to exit with code 1 and print an error (matching the existing `--name requires a value` style of reporting errors via `console.error` + `process.exit(1)`).
- All existing tests in `tests/cli.test.js` keep passing.
- At least one new test is added to `tests/cli.test.js` covering the `--format json` path (valid JSON, single line, contains the version).

## Constraints

- Only `bin/cli.js` and `tests/cli.test.js` may be modified.
- No new npm dependencies — use built-in `JSON.stringify`.
- Do not modify the `hello` subcommand, `--help`/`-h`, or the unknown-command branch.
- Code unrelated to the `version`/`--format` feature (including existing comments, the unused `parseGreetingFormat` helper, and formatting) must remain byte-for-byte unchanged.

## Out of Scope

- Any subcommand other than `version`.
- Refactoring or cleanup of unrelated code (e.g. the `parseGreetingFormat` TODO, the `hello --greeting` TODO).
- Adding `--format` support to any command other than `version`.

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
