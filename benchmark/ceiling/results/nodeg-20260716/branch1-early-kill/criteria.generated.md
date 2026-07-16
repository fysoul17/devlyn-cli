## Requirements
- Add a `--format json` option to the `version` subcommand in `bin/cli.js`; with the flag, print a single-line valid JSON object `{"version":"<x.y.z>"}` to stdout.
- Without `--format`, `version` keeps printing the bare version string exactly as it does today.
- `--format yaml` (or any other unsupported value) exits with code 1 and prints an error.
- Existing tests in `tests/cli.test.js` keep passing.
- Add at least one new test in `tests/cli.test.js` covering the `--format json` path.

## Constraints
- Only `bin/cli.js` and `tests/cli.test.js` may be modified.
- No new npm dependencies.
- Code unrelated to the version feature, including comments and formatting, must remain exactly as-is.

## Out of Scope
- Any other subcommand (`hello`, `--help`) or other files.
- Refactoring or cleanup of unrelated code (e.g. the unused `parseGreetingFormat` helper).

<!-- devlyn:verification -->
## Verification
```json
{
  "verification_commands": [
    { "cmd": "node bin/cli.js version", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\"0.1.0\"}"] },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1 },
    { "cmd": "npm test", "exit_code": 0 }
  ]
}
```
