## Requirements

- The `version` subcommand in `bin/cli.js` accepts a `--format json` flag. When passed, it prints valid single-line JSON `{"version":"<x.y.z>"}` where `<x.y.z>` is the version from `package.json` (same value `readPackageVersion()` currently returns).
- Without `--format`, the `version` subcommand keeps printing the current bare version string — unchanged behavior.
- `--format yaml` (or any other value that is not `json`) causes the CLI to print an error and exit with code 1.
- Existing tests in `tests/cli.test.js` keep passing; at least one new test exercises the `--format json` path (asserts the printed line parses as JSON and has a `version` key matching the semver pattern).
- Only `bin/cli.js` and `tests/cli.test.js` are touched. No other subcommand (`hello`, `--help`), no other file (`server/`, `web/`, `package.json`, etc.), and no new npm dependency. Code unrelated to the `version --format` feature — including existing comments and formatting, e.g. the `parseGreetingFormat` TODO helper — remains byte-for-byte as-is.

## Constraints

- Match the existing flag-parsing and error style already used in `bin/cli.js` (`parseNameFlag`'s `console.error(...); process.exit(1);` pattern for invalid input).
- Use only Node built-ins (`JSON.stringify`) — no new dependencies, consistent with `package.json` having no `devDependencies`.
- New test(s) follow the existing `node:test` + `node:assert` + `execFileSync` pattern already used in `tests/cli.test.js`.

## Out of Scope

- The `hello` subcommand and the pre-existing unused `parseGreetingFormat` helper (already marked TODO/out-of-scope in the source).
- Any subcommand other than `version`, and any file other than `bin/cli.js` / `tests/cli.test.js`.
- Refactoring or cleanup of unrelated code, comments, or formatting.

<!-- devlyn:verification -->
## Verification

- `node --test tests/` exits 0 (full suite, including the new test, passes).
- `node bin/cli.js version --format json` prints a single line of valid JSON `{"version":"<x.y.z>"}` matching the version in `package.json`.
- `node bin/cli.js version` prints the current bare version string, unchanged.
- `node bin/cli.js version --format yaml` exits with code 1 and prints an error (stderr).
