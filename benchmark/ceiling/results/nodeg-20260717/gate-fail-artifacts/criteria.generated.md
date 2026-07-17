## Goal (verbatim)

```
Add a `--format json` option to the `version` subcommand in `bin/cli.js`. With the flag, output should be valid JSON: `{"version":"<x.y.z>"}` (single line). Without the flag, keep the current bare version string.

`--format yaml` (or any other unsupported value) should exit 1 with an error.

Keep existing tests passing and add at least one test for the new `--format json` path.

Only touch `bin/cli.js` and `tests/cli.test.js`. Do not modify other subcommands or other files. No new npm dependencies.

Code unrelated to the requested version feature, including comments and formatting, must remain exactly as-is. Refactoring or cleanup of unrelated code is out of scope.
```

## Context anchors (non-binding)

- `bin/cli.js:59-62` — current `version` case: `console.log(readPackageVersion())`, reading version from `package.json` via `readPackageVersion()`.
- `tests/cli.test.js:22-25` — existing test `version prints package version` asserts `run(['version'])` stdout matches `/\d+\.\d+\.\d+/`.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "node bin/cli.js version", "exit_code": 0, "stdout_contains": [], "stdout_not_contains": ["{"] },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":"], "stdout_not_contains": [] },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1, "stdout_contains": [], "stdout_not_contains": [] },
    { "cmd": "npm test", "exit_code": 0, "stdout_contains": [], "stdout_not_contains": [] }
  ]
}
```
