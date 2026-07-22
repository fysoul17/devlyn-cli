# Generated criteria — add `--format json` to `version` subcommand

## Requirements

- `bin/cli.js`'s `version` subcommand accepts an optional `--format json` flag; when present, stdout is a single line of valid JSON: `{"version":"<x.y.z>"}` where `<x.y.z>` is the version read via the existing `readPackageVersion()` (from `package.json`).
- Without `--format`, the `version` subcommand's behavior is unchanged: print the bare version string via `console.log(readPackageVersion())`.
- `--format yaml`, or any `--format` value other than `json`, causes the CLI to exit with status code 1 and print an error (following the existing `parseNameFlag` pattern of `console.error(...)` + `process.exit(1)`).
- All existing tests in `tests/cli.test.js` keep passing; at least one new test covers the `--format json` path (exercised via the existing `run()` helper in that file).
- Only `bin/cli.js` and `tests/cli.test.js` are modified. No other files, and no new npm dependencies (use `JSON.stringify`, already a Node built-in).

## Constraints

- New flag parsing must follow the existing style in `bin/cli.js` (cf. `parseNameFlag`, switch-based command dispatch, `case 'version':` block at bin/cli.js:59-62).
- Code unrelated to this feature — comments (including the `TODO(devlyn)` and `TODO` comments), formatting, other subcommands (`hello`, `--help`/`-h`, unknown-command handling) — must remain byte-for-byte unchanged. No unrelated refactor or cleanup.
- `readPackageVersion()` stays the single source of truth for the version value in both the bare and JSON output paths.

## Out of Scope

- Any subcommand other than `version` (`hello`, `--help`/`-h`, unknown-command fallback).
- The pre-existing unused `parseGreetingFormat` helper and its TODO comments — leave as-is.
- Any file other than `bin/cli.js` and `tests/cli.test.js`.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "npm test", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\"0.1.0\"}"] },
    { "cmd": "node bin/cli.js version", "exit_code": 0, "stdout_contains": ["0.1.0"] },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1, "stdout_contains": ["Unsupported version format"] }
  ]
}
```