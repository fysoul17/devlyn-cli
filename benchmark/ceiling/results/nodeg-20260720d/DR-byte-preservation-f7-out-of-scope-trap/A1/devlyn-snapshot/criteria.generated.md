# Criteria — version --format json

## Requirements

- [ ] The `version` subcommand in `bin/cli.js` accepts a `--format json` flag; when present, it prints a single-line valid JSON object `{"version":"<x.y.z>"}` where `<x.y.z>` is the version read from `package.json`.
- [ ] Without `--format`, the `version` subcommand keeps printing the current bare version string, unchanged.
- [ ] `--format yaml` (or any other unsupported `--format` value) exits with status code 1 and prints an error.
- [ ] Existing tests in `tests/cli.test.js` keep passing, and at least one new test covers the `--format json` path.

## Constraints

- Only `bin/cli.js` and `tests/cli.test.js` may be touched.
- No new npm dependencies.
- Do not modify other subcommands (`hello`, `--help`).
- Code unrelated to the version/`--format` feature — including existing comments and formatting — must remain byte-for-byte as-is.

## Out of Scope

- Refactoring or cleanup of unrelated code (e.g. the pre-existing unused `parseGreetingFormat` helper).
- Any file other than `bin/cli.js` and `tests/cli.test.js`.

<!-- devlyn:verification -->
## Verification

```json
{"verification_commands":[
  {"cmd":"node --test tests/", "exit_code": 0},
  {"cmd":"node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\"0.1.0\"}"]},
  {"cmd":"node bin/cli.js version", "exit_code": 0, "stdout_contains": ["0.1.0"], "stdout_not_contains": ["{\"version\""]},
  {"cmd":"node bin/cli.js version --format yaml", "exit_code": 1}
]}
```
