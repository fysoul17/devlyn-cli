## Requirements

- [ ] Add a `--format json` option to the `version` subcommand in `bin/cli.js`.
- [ ] With `--format json`, print a single-line valid JSON object `{"version":"<x.y.z>"}` to stdout, where `<x.y.z>` is the same version value the plain `version` command already reads from `package.json`.
- [ ] Without `--format`, keep the current bare version string output unchanged.
- [ ] `--format yaml` (or any other unsupported `--format` value) exits with code 1 and prints an error.
- [ ] Keep all existing tests passing and add at least one new test in `tests/cli.test.js` for the `--format json` path.

## Constraints

- Only `bin/cli.js` and `tests/cli.test.js` may be touched.
- No new npm dependencies (JSON output uses `JSON.stringify`, already a built-in).
- Do not modify the `hello` subcommand, `--help`/`-h`, or the unknown-command path.
- Match the existing error style already used in `bin/cli.js` (`console.error(...)` + `process.exit(1)`, as in `parseNameFlag`).
- Code unrelated to the `--format` feature — including comments and formatting — must remain byte-for-byte as-is; this explicitly includes the two pre-existing `TODO` comments and the unused `parseGreetingFormat` helper, none of which this feature touches.

## Out of Scope

- Any subcommand other than `version`.
- Refactoring or cleanup of unrelated code, including the dead `parseGreetingFormat` helper.
- Adding a YAML parser/serializer or any other dependency to support `--format yaml` — it must simply be rejected.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\"0.1.0\"}"] },
    { "cmd": "node bin/cli.js version", "exit_code": 0, "stdout_contains": ["0.1.0"], "stdout_not_contains": ["{\"version\""] },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1 }
  ]
}
```
