# Generated criteria — --format json for version subcommand

## Requirements

- Add a `--format json` option to the `version` subcommand in `bin/cli.js`. With the flag, stdout must be valid single-line JSON: `{"version":"<x.y.z>"}` (exact key `version`, value from `package.json`).
- Without `--format`, the `version` subcommand keeps its current behavior: prints the bare version string with `console.log`.
- `--format yaml`, or any other unsupported `--format` value, exits with code 1 and prints an error (unsupported-format case).
- Existing tests in `tests/cli.test.js` continue to pass unmodified in behavior (the file may gain new tests but existing assertions must still hold).
- Add at least one new test in `tests/cli.test.js` covering the `--format json` path (asserts output is valid JSON with the expected shape).

## Constraints

- Only `bin/cli.js` and `tests/cli.test.js` may be touched. No other files (including `server/`, `scripts/`, `package.json`) may change.
- No new npm dependencies — JSON serialization uses the built-in `JSON.stringify`.
- Code unrelated to the version/--format feature — including existing comments, the `hello` command, `parseGreetingFormat`, `parseNameFlag`, `USAGE`, formatting/whitespace elsewhere — must remain byte-for-byte as-is. No unrelated refactor or cleanup.
- Follow the existing style in `bin/cli.js` (plain `switch` cases in `main()`, `console.log`/`console.error`/`process.exit` for errors, no new abstractions unless required for the single new flag).

## Out of Scope

- Any other subcommand (`hello`, `--help`/`-h`, top-level usage text) beyond what is strictly required to keep them working unchanged.
- Removing or wiring up the pre-existing unused `parseGreetingFormat` helper (pre-existing dead code, not touched by this feature).
- Adding a `--format` option to any command other than `version`.
- Supporting any `--format` value other than the implicit default (bare string) and `json`.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "expect_exit": 0 },
    { "cmd": "node bin/cli.js version --format json", "expect_exit": 0, "expect_stdout_regex": "^\\{\"version\":\"\\d+\\.\\d+\\.\\d+\"\\}\\n?$" },
    { "cmd": "node bin/cli.js version", "expect_exit": 0, "expect_stdout_regex": "^\\d+\\.\\d+\\.\\d+\\n?$" },
    { "cmd": "node bin/cli.js version --format yaml", "expect_exit": 1 }
  ]
}
```
