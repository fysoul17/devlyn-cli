# Generated criteria — add `--format json` to `version` subcommand

## Requirements

- [ ] `bin/cli.js`: the `version` subcommand accepts an optional `--format json` flag. When passed, print a single line of valid JSON: `{"version":"<x.y.z>"}` using the real package version from `readPackageVersion()`.
- [ ] `bin/cli.js`: without `--format`, `version` keeps printing the current bare version string (unchanged behavior).
- [ ] `bin/cli.js`: `--format yaml` (or any other unsupported value) exits with code 1 and prints an error.
- [ ] `tests/cli.test.js`: existing tests keep passing; add at least one new test for the `--format json` path.

## Constraints

- Only touch `bin/cli.js` and `tests/cli.test.js`. Do not modify other subcommands (`hello`, `--help`) or any other file.
- No new npm dependencies — `JSON.stringify`/`JSON.parse` are built-in.
- Code unrelated to the version feature, including comments and formatting, must remain exactly as-is (e.g. the existing `TODO(devlyn)` / `TODO` comments and the unused `parseGreetingFormat` helper stay untouched).
- Match the existing code style: flag parsing follows the `parseNameFlag` pattern (read from `rest`/`argv`, `console.error` + `process.exit(1)` on invalid input); command dispatch stays inside the existing `switch (command)` block.

## Out of Scope

- Do not add a `--format` flag to `hello` or any other subcommand.
- Do not remove, rename, or "clean up" the unused `parseGreetingFormat` helper or its TODO comments — they are pre-existing and out of scope.
- Do not change `package.json`, `USAGE` text wording beyond what the feature requires, or add a JSON parsing/formatting dependency.

<!-- devlyn:verification -->
## Verification

```json
{"verification_commands": [
  {"cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\""]},
  {"cmd": "node bin/cli.js version", "exit_code": 0, "stdout_not_contains": ["{\"version\":\""]},
  {"cmd": "node bin/cli.js version --format yaml", "exit_code": 1},
  {"cmd": "node --test tests/", "exit_code": 0}
]}
```
