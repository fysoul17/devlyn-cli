# Generated criteria (free-form, medium complexity)

## Requirements

- Add `--format json` support to the `version` subcommand in `bin/cli.js`. When the flag is passed, print single-line valid JSON to stdout: `{"version":"<x.y.z>"}`.
- Without `--format`, the `version` subcommand keeps printing the current bare version string (unchanged behavior).
- `--format yaml`, or any other value not equal to `json`, causes `version` to exit with code 1 and print an error (existing error pattern: `console.error(...)` then `process.exit(1)`, as in `parseNameFlag` at bin/cli.js:37-40 and the unknown-command branch at bin/cli.js:63-66).
- Add at least one new test in `tests/cli.test.js` exercising the `--format json` path, following the existing `execFileSync`/`assert` pattern used by the other tests in that file.
- All pre-existing tests (`tests/cli.test.js`, `tests/server.test.js`) continue to pass unmodified.

## Constraints

- Only `bin/cli.js` and `tests/cli.test.js` may be touched. No other file (package.json, server/, web/, README.md, playwright.config.js) changes.
- No new npm dependencies — `JSON.stringify` (native) is sufficient for the single-line JSON output.
- Code unrelated to the `version`/`--format` feature — comments, formatting, the unused `parseGreetingFormat` helper (bin/cli.js:29-31, explicitly marked out of scope by its own TODO), the `hello` subcommand, the USAGE banner — must remain byte-identical.
- Follow the existing code shape: the `version` case in the `switch` (bin/cli.js:59-62), the flag-parsing style of `parseNameFlag` (bin/cli.js:33-42), and the error+exit(1) pattern already used twice in this file.

## Out of Scope

- The `hello` subcommand, its `--name` flag, and the unused `parseGreetingFormat` helper.
- Any file other than `bin/cli.js` and `tests/cli.test.js`.
- Any refactor, cleanup, or reformatting of code not required by this feature.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\"0.1.0\"}"] },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1 }
  ]
}
```
