# Generated Criteria — `--format json` for the `version` subcommand

## Requirements

- Add a `--format json` option to the `version` subcommand in `bin/cli.js`. With the flag, print a single line of valid JSON: `{"version":"<x.y.z>"}`, using the version read from `package.json`.
- Without `--format json`, `version` must keep printing the bare version string exactly as it does today (no behavior change).
- `--format yaml` (or any other unsupported `--format` value) must exit with code 1 and print an error.
- All existing tests in `tests/cli.test.js` must keep passing.
- Add at least one new test in `tests/cli.test.js` covering the `--format json` path.

## Constraints

- Only `bin/cli.js` and `tests/cli.test.js` may be modified.
- No new npm dependencies.
- Code unrelated to the `version`/`--format` feature — including comments and formatting — must remain byte-for-byte unchanged. In particular, the `hello` command, `USAGE` text, and the pre-existing unused `parseGreetingFormat` helper (with its TODO comments) must not be touched, reused, or removed.

## Out of Scope

- Any subcommand other than `version` (`hello`, `--help`).
- Refactoring, cleanup, or reuse of unrelated code such as `parseGreetingFormat` — it backs the `hello` greeting path, not `version`, despite the similar name.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "node bin/cli.js version", "exit_code": 0, "stdout_not_contains": ["{"] },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\"0.1.0\"}"] },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1 },
    { "cmd": "node --test tests/cli.test.js", "exit_code": 0 }
  ]
}
```
