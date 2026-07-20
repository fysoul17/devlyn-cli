## Requirements

- Add a `--format json` option to the `version` subcommand in `bin/cli.js`. With the flag, the command outputs valid single-line JSON: `{"version":"<x.y.z>"}`, where `<x.y.z>` is the value already returned by `readPackageVersion()`.
- Without `--format` (default behavior), `version` keeps printing the current bare version string exactly as today.
- `--format yaml` (or any other unsupported `--format` value) exits the process with code 1 and prints an error.
- All existing tests in `tests/cli.test.js` keep passing unmodified.
- At least one new test in `tests/cli.test.js` exercises the `--format json` path (parses the output as JSON and asserts the `version` key/shape).

## Constraints

- Only `bin/cli.js` and `tests/cli.test.js` may be touched. Do not modify other subcommands (`hello`, `--help`/usage) or any other file.
- No new npm dependencies — implement the flag parsing and JSON serialization with built-ins already available (e.g. `JSON.stringify`), following the existing flag-parsing style (`parseNameFlag`).
- Code unrelated to the version/`--format` feature — including existing comments and formatting — must remain byte-for-byte unchanged. No refactors or unrelated cleanup.

## Out of Scope

- Any other subcommand's runtime behavior (`hello`, top-level `--help`).
- Supporting `--format` values other than `json` (e.g. `yaml`) beyond the required exit-1 error path.
- Any new dependency for JSON/YAML handling.

<!-- devlyn:verification -->
## Verification

- `node bin/cli.js version --format json` prints a single line of valid JSON matching `{"version":"<x.y.z>"}` where `<x.y.z>` matches `/^\d+\.\d+\.\d+$/`.
- `node bin/cli.js version` (no flag) still prints the bare version string (unchanged from current behavior).
- `node bin/cli.js version --format yaml` exits with code 1 and prints an error.
- `npm test` passes, including the existing three CLI tests plus a new `--format json` test.
