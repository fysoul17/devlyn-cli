# Generated criteria — CLI `version --format json`

## Requirements

- Add a `--format json` option to the `version` subcommand in `bin/cli.js`. When passed, output must be a single line of valid JSON: `{"version":"<x.y.z>"}` using the real version from `package.json`.
- Without `--format` (or with no format flag), `version` keeps printing the current bare version string (unchanged behavior).
- `--format yaml`, or any other unsupported `--format` value, must exit with code `1` and print an error.
- Existing tests must keep passing.
- Add at least one new test covering the `--format json` path (`tests/cli.test.js`).

## Constraints

- Only `bin/cli.js` and `tests/cli.test.js` may be touched.
- Do not modify other subcommands (`hello`, `--help`) or any other file.
- No new npm dependencies.
- Code unrelated to the version feature — including comments and formatting — must remain byte-for-byte as-is. No unrelated refactor/cleanup (e.g. the existing `parseGreetingFormat` dead-code TODO in `bin/cli.js` is explicitly out of scope and must not be touched).

## Out of Scope

- Any subcommand other than `version`.
- Any file other than `bin/cli.js` and `tests/cli.test.js`.
- Formats other than `json` (only need to reject them with exit 1).

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "node bin/cli.js version", "expect_type": "stdout_match", "expect": "^\\d+\\.\\d+\\.\\d+$" },
    { "cmd": "node bin/cli.js version --format json", "expect_type": "stdout_match", "expect": "^\\{\"version\":\"\\d+\\.\\d+\\.\\d+\"\\}$" },
    { "cmd": "node bin/cli.js version --format yaml", "expect_type": "exit_code", "expect": "1" },
    { "cmd": "npm test", "expect_type": "exit_code", "expect": "0" }
  ]
}
```
