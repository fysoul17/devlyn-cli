# Generated criteria (free-form, medium complexity)

## Requirements

- [ ] The `version` subcommand in `bin/cli.js` accepts a `--format json` flag. When passed, it prints a single line of valid JSON: `{"version":"<x.y.z>"}` (the version read from `package.json`) and exits 0.
- [ ] Without `--format`, the `version` subcommand keeps its current behavior: print the bare version string and exit 0.
- [ ] Passing `--format yaml`, or any other value not equal to `json`, exits with code 1 and prints an error (no successful version output).
- [ ] All existing tests in `tests/cli.test.js` continue to pass.
- [ ] At least one new test is added to `tests/cli.test.js` exercising the `--format json` path.

## Constraints

- Only `bin/cli.js` and `tests/cli.test.js` may be modified.
- Do not modify the `hello` command, `--help` output, or any other existing subcommand behavior.
- No new npm dependencies (no changes to `package.json` `dependencies`/`devDependencies`).
- Code unrelated to the `version --format` feature — including existing comments, TODOs, and formatting (e.g. `parseGreetingFormat`, the `hello` command) — must remain byte-for-byte as-is. No refactoring or cleanup of unrelated code.

## Out of Scope

- Any subcommand other than `version`.
- Adding a `--format` flag to any command other than `version`.
- Dependency additions or upgrades.
- Cleanup/refactor of pre-existing unrelated code (e.g. the unused `parseGreetingFormat` helper).

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "node --test tests/",
      "exit_code": 0
    },
    {
      "cmd": "node bin/cli.js version",
      "exit_code": 0,
      "stdout_contains": ["0.1.0"],
      "stdout_not_contains": ["{\"version\""]
    },
    {
      "cmd": "node bin/cli.js version --format json",
      "exit_code": 0,
      "stdout_contains": ["{\"version\":\"0.1.0\"}"]
    },
    {
      "cmd": "node bin/cli.js version --format yaml",
      "exit_code": 1
    }
  ]
}
```
