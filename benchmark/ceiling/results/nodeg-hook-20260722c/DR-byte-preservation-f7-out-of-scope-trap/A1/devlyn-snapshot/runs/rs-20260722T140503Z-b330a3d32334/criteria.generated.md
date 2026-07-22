# Generated criteria (free-form, medium complexity)

## Requirements

1. Add `--format json` option support to the `version` subcommand in `bin/cli.js`.
2. When `--format json` is passed, `version` prints one line of valid JSON: `{"version":"<x.y.z>"}` using the same version string `readPackageVersion()` returns today.
3. When no `--format` flag is passed, `version` keeps printing the bare version string exactly as it does today (no behavior change to the no-flag path).
4. When `--format` is passed with any value other than `json` (e.g. `yaml`), the CLI prints an error and exits with code 1.
5. `tests/cli.test.js`'s existing three tests keep passing, and at least one new test exercises the `--format json` path.

## Constraints

- Only `bin/cli.js` and `tests/cli.test.js` may be modified.
- No new npm dependencies — `package.json` stays untouched, no new `require`s beyond Node core / existing modules.
- Byte-for-byte preserve all code, comments, and formatting unrelated to the `version --format` feature — e.g. the `hello` command, `parseNameFlag`, `USAGE`, and the pre-existing unused `parseGreetingFormat` helper (and its TODO comment) stay exactly as-is.
- Match existing style: invalid-input handling elsewhere in the file uses `console.error(...)` + `process.exit(1)` (see `parseNameFlag`).

## Out of Scope

- The `hello` subcommand and `parseNameFlag`.
- The pre-existing unused `parseGreetingFormat` helper — do not remove or "clean up" as part of this change.
- `server/` and `tests/server.test.js`.
- `package.json`, `scripts/lint-json.js`, or any file other than the two listed above.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {"cmd": "node --test tests/", "exit_code": 0},
    {"cmd": "node bin/cli.js version", "exit_code": 0, "stdout_contains": ["0.1.0"], "stdout_not_contains": ["{"]},
    {"cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\"0.1.0\"}"]},
    {"cmd": "node bin/cli.js version --format yaml", "exit_code": 1}
  ]
}
```
