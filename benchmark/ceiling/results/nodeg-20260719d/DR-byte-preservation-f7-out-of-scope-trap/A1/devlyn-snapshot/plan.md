# Plan — add `--format json` to `version` subcommand

<!-- devlyn:authorized-surface -->
## 1. Files to touch

- `bin/cli.js` (edit) — add a `--format` flag reader for the `version` subcommand (following the existing `parseNameFlag` pattern: read from `rest`, `console.error` + `process.exit(1)` on invalid input) and branch the `case 'version':` body to print `{"version":"<x.y.z>"}` when `--format json` is passed, print the bare version when no `--format` is passed, and error-exit(1) for any other `--format` value. Satisfies Requirements 1–3 (JSON output, unchanged bare-string default, reject unsupported formats).
- `tests/cli.test.js` (edit) — add a test asserting `version --format json` prints valid single-line JSON with a `version` field matching `\d+\.\d+\.\d+`, and a test asserting `version --format yaml` exits with code 1 (via `execFileSync` catching the thrown error / checking `status`). Existing tests (`hello default`, `hello with --name`, `version prints package version`) stay untouched. Satisfies Requirement 4.

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## 2. Risks

- **Out-of-scope expansions to refuse**: do not add `--format` to `hello` or `--help`; do not touch `USAGE` text; do not remove/rename/"clean up" the unused `parseGreetingFormat` helper or its `TODO(devlyn)`/`TODO` comments; do not touch `package.json`. Any of these would violate the stated Constraints/Out of Scope sections verbatim.
- **Ambiguous spec section, interpreted strictly**: the spec says "`--format yaml` (or any other unsupported value) exits with code 1 and prints an error." This is read to also cover `--format` passed with no following value (e.g. trailing `--format` with nothing after it, or the next token starting with `-`), by direct analogy to `parseNameFlag`'s existing "requires a value" handling — that is the only precedent in this file for a flag-value-parsing failure, so the same shape (`console.error` + `process.exit(1)`) is reused rather than inventing new error-handling style.
- **Known failure mode**: `console.log` vs `console.error` must be picked correctly — JSON success output goes to stdout via `console.log`/`process.stdout`, error output goes to stderr via `console.error`, matching the existing `hello`/default-case convention in the file so verification's `stdout_contains`/`stdout_not_contains` checks work against the right stream.
- **Known failure mode**: the JSON must be emitted as a single line with no trailing formatting (`console.log(JSON.stringify({version}))`, not pretty-printed) to satisfy "print a single line of valid JSON."
- **Known failure mode**: the unrelated `version` test (`version prints package version`) must keep passing unmodified — the bare-string path must remain byte-for-byte the same `console.log(readPackageVersion())` output shape it is today.

## 3. Acceptance restatement

```json
{"verification_commands": [
  {"cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\""]},
  {"cmd": "node bin/cli.js version", "exit_code": 0, "stdout_not_contains": ["{\"version\":\""]},
  {"cmd": "node bin/cli.js version --format yaml", "exit_code": 1},
  {"cmd": "node --test tests/", "exit_code": 0}
]}
```
