# Generated criteria — CLI `version --format json`

## Requirements

- Add a `--format json` option to the `version` subcommand in `bin/cli.js`. With the flag, print a single-line, valid JSON object `{"version":"<x.y.z>"}` to stdout.
- Without `--format` (or with no flag at all), `version` keeps printing the current bare version string, unchanged.
- `--format yaml` (or any other unsupported `--format` value) exits with code 1 and prints an error.
- Existing tests in `tests/cli.test.js` keep passing.
- Add at least one new test in `tests/cli.test.js` covering the `--format json` path.

## Constraints

- Only touch `bin/cli.js` and `tests/cli.test.js`.
- No new npm dependencies — use the built-in `JSON.stringify`/`JSON.parse`.
- Code unrelated to the requested version feature — including comments, formatting, and other subcommands (e.g. `hello`) — must remain byte-identical. No incidental refactors or cleanup.

## Out of Scope

- Any subcommand other than `version`.
- Any file other than `bin/cli.js` and `tests/cli.test.js`.
- The pre-existing unused `parseGreetingFormat` helper and its TODO comment — leave as-is.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "node bin/cli.js version",
      "exit_code": 0,
      "stdout_contains": ["0.1.0"],
      "stdout_not_contains": ["{"]
    },
    {
      "cmd": "node bin/cli.js version --format json",
      "exit_code": 0,
      "stdout_contains": ["{\"version\":\"0.1.0\"}"]
    },
    {
      "cmd": "node bin/cli.js version --format yaml",
      "exit_code": 1
    },
    {
      "cmd": "node --test tests/",
      "exit_code": 0
    }
  ]
}
```
