# Generated criteria — --format json for `version` subcommand

## Requirements

- The `version` subcommand in `bin/cli.js` accepts a `--format json` flag. When passed, stdout is exactly one line of valid JSON: `{"version":"<x.y.z>"}`, where `<x.y.z>` is the version from `package.json`.
- Without `--format`, the `version` subcommand keeps printing the current bare version string exactly as before (no behavior change).
- `--format yaml`, or any other unsupported `--format` value, causes the CLI to exit with code 1 and print an error (not the bare version, not JSON).
- All existing tests in `tests/cli.test.js` continue to pass.
- At least one new test in `tests/cli.test.js` covers the `--format json` path.

## Constraints

- Only `bin/cli.js` and `tests/cli.test.js` may be modified.
- No new npm dependencies — use built-in `JSON.stringify`/`JSON.parse` only.
- Do not modify other subcommands (`hello`, `--help`/`-h`) or their behavior.
- Code unrelated to the version feature — including comments, TODOs, and formatting elsewhere in `bin/cli.js` — must remain byte-for-byte as-is. No unrelated refactoring or cleanup.

## Out of Scope

- Any other subcommand's behavior or flags.
- Cleanup of pre-existing dead code (e.g. the unused `parseGreetingFormat` helper) or its TODO comments.
- Adding `--format` support to any subcommand other than `version`.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["\"version\":"] },
    { "cmd": "node bin/cli.js version", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1 }
  ]
}
```
