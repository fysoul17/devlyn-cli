# Plan — add `--format json` to the `version` subcommand

<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — `edit`. Add a `parseFormatFlag(argv)` helper (modeled on `parseNameFlag`, `bin/cli.js:33-42`) and modify the `case 'version':` block (`bin/cli.js:59-62`) to branch on the parsed format: `JSON.stringify({version})` when `--format json` is present, unchanged bare `console.log(readPackageVersion())` otherwise, `console.error(...)` + `process.exit(1)` for any other `--format` value (Requirements 1-3).
- `tests/cli.test.js` — `edit`. Add at least one new `test(...)` block asserting the `--format json` path emits valid, single-line JSON with a `version` key matching the package version (Requirement 5). Existing three tests (`bin/cli.js` lines 12-25 of the test file) are left byte-for-byte unchanged (Requirement 4).

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Out-of-scope expansions to refuse**: do not touch `hello`, `--help`/`-h`, `USAGE` text, or the dead `parseGreetingFormat` helper (`bin/cli.js:27-31`, explicitly marked out-of-scope by its own comment) — Out of Scope items 1 and 3, Constraint "Do not modify the `hello` subcommand...".
- **No new dependencies**: use `JSON.stringify`, already a built-in — Constraint "No new npm dependencies".
- **Byte-for-byte preservation**: all lines outside the `version` case and the new helper (comments, `USAGE`, `hello` case, `parseNameFlag`, `main`, trailing `main(process.argv.slice(2));`) must remain unchanged — Constraint "Code unrelated to the version/`--format` feature ... must remain byte-for-byte unchanged."
- **Ambiguous spec section — `--format` with no value or with a flag-like next token**: the criteria only enumerates `--format yaml` as the "unsupported value" example and doesn't state behavior when `--format` is given with a missing/absent value. Interpreting strictly: Requirement 3 says "`--format` value other than `json`" causes exit 1 — a missing value is not `json`, so it falls under the same exit-1 path (explicit `console.error` + `process.exit(1)`, no silent fallback, consistent with repo's Error Handling Philosophy). This is not tested by the generated verification commands but keeps the contract internally consistent; do not add a distinct error message/flag for this sub-case beyond reusing the same explicit-error pattern.
- **Known failure mode — output must stay single-line valid JSON**: `JSON.stringify({version: X})` produces no embedded newlines by construction; using `console.log` (as the existing bare-version path already does) appends exactly one trailing newline, matching "single line" semantics already relied upon by the existing `version prints package version` test.
- **Known failure mode — literal JSON shape**: the key must be exactly `version` (lowercase, matching Requirement's literal `{"version":"<x.y.z>"}`), and the value must be the exact string from `readPackageVersion()` (no added/removed whitespace, no extra keys).
- **Test placement**: new test(s) appended to `tests/cli.test.js` without altering the three existing `test(...)` blocks or the `run()` helper (lines 1-11), so existing tests keep passing unmodified in behavior.

## Acceptance restatement

<!-- devlyn:verification -->
## Verification

```json
{"verification_commands":[
  {"cmd":"node bin/cli.js version", "exit_code":0, "stdout_contains":["0.1.0"]},
  {"cmd":"node bin/cli.js version --format json", "exit_code":0, "stdout_contains":["{\"version\":\"0.1.0\"}"]},
  {"cmd":"node bin/cli.js version --format yaml", "exit_code":1},
  {"cmd":"npm test", "exit_code":0}
]}
```
