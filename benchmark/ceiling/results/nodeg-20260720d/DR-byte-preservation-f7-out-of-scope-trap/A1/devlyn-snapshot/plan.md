# Plan — version --format json

<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — `edit`: add `--format json` handling to the `case 'version':` branch (bin/cli.js:59-62). Requirement: "`version` subcommand accepts a `--format json` flag; when present, prints single-line valid JSON `{"version":"<x.y.z>"}`" and "`--format yaml` (or any other unsupported value) exits with status code 1 and prints an error." Bare `version` (no `--format`) must keep printing via the existing `console.log(readPackageVersion())` path unchanged.
- `tests/cli.test.js` — `edit`: add new `test(...)` block(s) after the existing `'version prints package version'` test (tests/cli.test.js:22-25). Requirement: "at least one new test covers the `--format json` path"; existing three tests (`hello default`, `hello with --name`, `version prints package version`) must keep passing unmodified.

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Out-of-scope refusal**: `parseGreetingFormat` (bin/cli.js:29-31) is a pre-existing unused helper with its own TODO marking it out of scope. Do not touch, rename, remove, or wire it up — the new `--format` parsing for `version` is a distinct, separately-implemented flag, not a reuse of this helper (reusing it would silently couple two unrelated features and violate "Do not modify other subcommands").
- **Do not touch `hello` or `--help`**: constraint explicitly forbids modifying other subcommands. The `USAGE` string (bin/cli.js:8-19) documents `hello`/`version`/`--help` only — criteria does not require documenting `--format json` in USAGE, so leave `USAGE` byte-for-byte unchanged (adding an undocumented-in-help flag is acceptable; inventing a documentation requirement not in the criteria would be scope creep).
- **Byte-for-byte constraint**: "Code unrelated to the version/`--format` feature — including existing comments and formatting — must remain byte-for-byte as-is." This means the diff must be additive/localized to the `case 'version':` block only; no reformatting of surrounding lines, no touching `parseNameFlag`, `readPackageVersion`, `main`'s command dispatch structure, or the `hello`/default/`--help` branches.
- **Exact JSON shape**: verification requires `stdout_contains: ["{\"version\":\"0.1.0\"}"]` — a single-line JSON object with no spaces (matches `JSON.stringify({version: readPackageVersion()})` output exactly, since `JSON.stringify` produces `{"version":"0.1.0"}` with no extra whitespace by default). Must not pretty-print or add trailing content on that line beyond the newline `console.log` appends.
- **Unsupported `--format` values**: any `--format` value other than `json` (e.g. `yaml`, or `--format` with no value/a flag-like value) must exit code 1 and print an error (to stderr, consistent with existing error pattern in `parseNameFlag` at bin/cli.js:38 and the `default:` case at bin/cli.js:64-66, which use `console.error` + `process.exit(1)`). Follow that existing convention rather than inventing a new error-reporting style.
- **Flag parsing must not collide with `readPackageVersion`/other flags**: `version` currently takes no arguments; the new parsing only needs to inspect `rest` (the args after `version`) for `--format <value>`, mirroring the existing `parseNameFlag(rest)` pattern used by `hello` (bin/cli.js:33-42, called at bin/cli.js:55) for consistency, without modifying `parseNameFlag` itself.
- **Test file additions must not disturb existing tests**: `tests/cli.test.js` constraint requires existing tests keep passing verbatim — append new test(s) rather than editing the existing three `test(...)` blocks (lines 12-25) or the `run` helper (lines 8-10).

## Acceptance restatement

- [ ] The `version` subcommand in `bin/cli.js` accepts a `--format json` flag; when present, it prints a single-line valid JSON object `{"version":"<x.y.z>"}` where `<x.y.z>` is the version read from `package.json`.
- [ ] Without `--format`, the `version` subcommand keeps printing the current bare version string, unchanged.
- [ ] `--format yaml` (or any other unsupported `--format` value) exits with status code 1 and prints an error.
- [ ] Existing tests in `tests/cli.test.js` keep passing, and at least one new test covers the `--format json` path.

```json
{"verification_commands":[
  {"cmd":"node --test tests/", "exit_code": 0},
  {"cmd":"node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\"0.1.0\"}"]},
  {"cmd":"node bin/cli.js version", "exit_code": 0, "stdout_contains": ["0.1.0"], "stdout_not_contains": ["{\"version\""]},
  {"cmd":"node bin/cli.js version --format yaml", "exit_code": 1}
]}
```
