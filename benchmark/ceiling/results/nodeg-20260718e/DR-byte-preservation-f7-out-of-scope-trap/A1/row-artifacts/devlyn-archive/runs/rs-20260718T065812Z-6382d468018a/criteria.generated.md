# Criteria (generated — free-form mode, complexity: medium)

## Requirements

- [ ] Add a `--format json` option to the `version` subcommand in `bin/cli.js`. With the flag, output must be valid JSON on a single line: `{"version":"<x.y.z>"}` where `<x.y.z>` is the value from `package.json`.
- [ ] Without `--format json`, the `version` subcommand keeps its current behavior: print the bare version string (unchanged).
- [ ] `--format yaml`, or any other unsupported `--format` value, exits with code 1 and prints an error (does not print a version).
- [ ] All existing tests in `tests/cli.test.js` continue to pass.
- [ ] `tests/cli.test.js` gains at least one new test covering the `--format json` path.

## Constraints

- Touch only `bin/cli.js` and `tests/cli.test.js`. No other files.
- Do not modify the `hello` subcommand, `--help`/`-h`, or any other existing subcommand behavior.
- No new npm dependencies (`package.json` dependencies/devDependencies unchanged).
- Code unrelated to the `--format` feature — including existing comments and formatting in `bin/cli.js` and `tests/cli.test.js` — must remain byte-for-byte as-is. No unrelated refactor or cleanup.

## Out of Scope

- Any subcommand other than `version`.
- Any file other than `bin/cli.js` and `tests/cli.test.js`.
- Supporting `--format` values beyond `json` (e.g. `yaml`) as anything other than an error case.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "node bin/cli.js version", "exit_code": 0, "stdout_contains": [] },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\""] },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1 },
    { "cmd": "node --test tests/", "exit_code": 0 }
  ]
}
```
