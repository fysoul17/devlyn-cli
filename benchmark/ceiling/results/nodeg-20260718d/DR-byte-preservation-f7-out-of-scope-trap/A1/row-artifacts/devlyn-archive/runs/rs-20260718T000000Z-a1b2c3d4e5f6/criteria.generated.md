# Generated criteria — resolve run

Source: free-form goal (medium complexity). See `.devlyn/goal.raw.txt` for the verbatim goal text.

## Requirements

- [ ] `bin/cli.js` `version` subcommand accepts a `--format json` flag; when passed, stdout is a single line of valid JSON: `{"version":"<x.y.z>"}` using the same version string `readPackageVersion()` currently returns.
- [ ] Without `--format`, `version` keeps printing the current bare version string (no behavior change to the no-flag path).
- [ ] `--format yaml` or any other unsupported `--format` value exits with code 1 and prints an error (matching the existing CLI's error-handling idiom, e.g. `parseNameFlag`'s `console.error` + `process.exit(1)` pattern).
- [ ] Only `bin/cli.js` and `tests/cli.test.js` are touched. The `hello` subcommand's behavior is unchanged. `--help`/`USAGE` output may update only the `version` line to document the new `--format json` option (directly part of the version feature's own interface surface); all other `--help` content (header, `hello` line, examples) stays unchanged. No new npm dependencies.
- [ ] At least one new test in `tests/cli.test.js` covers the `--format json` path (valid JSON, contains `version` key matching semver shape); existing three tests (`hello default`, `hello with --name`, `version prints package version`) keep passing unmodified.

## Constraints

- Existing code style/comments/formatting elsewhere in `bin/cli.js` and `tests/cli.test.js` must remain byte-identical — this is an additive, scoped change, not a refactor.
- Follow the file's existing patterns: flag parsing style similar to `parseNameFlag`, error style similar to the `--name` validation and the `default:` case in the command switch (`console.error` + `process.exit(1)`).
- JSON output must be a single line (`JSON.stringify`, no pretty-printing).

## Out of Scope

- The `hello` command's behavior, and all `--help`/`USAGE` content except the `version` line's flag documentation (the version line may be updated to mention `--format json`, since that is directly part of the requested version feature's own interface, not unrelated code).
- Any other file in the repo.
- Refactoring or cleanup of unrelated code (e.g. `parseGreetingFormat`, the `hello --greeting` TODO) — explicitly called out as out of scope by the user.
- Adding new npm dependencies (e.g. a YAML library) — not needed since only JSON is a supported format.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "node bin/cli.js version", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1 },
    { "cmd": "npm test", "exit_code": 0 }
  ]
}
```
