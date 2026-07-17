# Plan — add `--format json` to `version` subcommand

<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — edit. Add `--format` parsing and branch the `version` case (currently `bin/cli.js:59-62`, `console.log(readPackageVersion())`) to emit compact JSON when `--format json` is passed, keep the bare string otherwise, and `process.exit(1)` with a stderr message for any other `--format` value. Binding clause: "Add a `--format json` option to the `version` subcommand... Without the flag, keep the current bare version string... `--format yaml` (or any other unsupported value) should exit 1 with an error."
- `tests/cli.test.js` — edit. Add at least one new test exercising `version --format json` (assert valid JSON with a `version` key matching `x.y.z`), alongside the existing `version prints package version` test (`tests/cli.test.js:22-25`) which stays untouched. Binding clause: "Keep existing tests passing and add at least one test for the new `--format json` path."

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Out-of-contract expansions to refuse**: do not touch the `hello` subcommand or `parseNameFlag` (`bin/cli.js:33-42`) beyond reading it as a pattern reference; do not touch the dead `parseGreetingFormat` helper (`bin/cli.js:27-31`, already commented as "unused... out of scope for the current feature") — it parses a *different* concept (greeting format) and removing/reusing it is a separate change not requested here; do not touch `package.json`, `USAGE` text, `server/`, or any file outside the two authorized paths; add no new npm dependencies (JSON encoding must use the built-in `JSON.stringify`, not a library).
- **Ambiguous binding clause — exact JSON shape**: the Goal pins the literal shape `{"version":"<x.y.z>"}` on a single line, no extra whitespace. `JSON.stringify({ version: readPackageVersion() })` (no indentation argument) produces exactly `{"version":"0.1.0"}` with no spaces after `:` — this must be used as-is, not `JSON.stringify(obj, null, 2)` or manual template-string concatenation, to avoid drifting from the pinned literal. The verification block's `stdout_contains: ["{\"version\":"]` confirms this exact prefix, and the bare-mode check `stdout_not_contains: ["{"]` confirms the unflagged path must never emit a brace.
- **Ambiguous binding clause — what counts as "unsupported value"**: interpret strictly — any `--format` value other than the literal string `json` is unsupported and exits 1, including `yaml`, an empty/missing value after `--format`, or unrecognized flags. Only the *absence* of `--format` entirely triggers the bare-string legacy path; presence of `--format` with anything but `json` is an error path, mirroring how `parseNameFlag` (`bin/cli.js:33-42`) already exits 1 with `console.error(...)` when a flag's value is missing/invalid — use the same `console.error` + `process.exit(1)` idiom for consistency with the existing file style.
- **Known failure mode — accidental multi-line/whitespace output**: `console.log(JSON.stringify(...))` appends exactly one trailing newline (same as the existing bare-string `console.log(readPackageVersion())`), which is consistent with "single line" and does not violate `stdout_not_contains` checks; must not pretty-print or add a trailing comma/space.
- **Known failure mode — flag parsing order**: `--format` must be detected via `rest.indexOf('--format')` (mirroring `parseNameFlag`'s `argv.indexOf('--name')` pattern) so it works regardless of position in `rest`; the `version` subcommand currently takes no other flags, so no interaction with other flags is expected, but the lookup must not assume `--format` is at a fixed index.
- **Known failure mode — untouched code must stay byte-identical**: the Goal explicitly requires "Code unrelated to the requested version feature, including comments and formatting, must remain exactly as-is." Only the `version` case body and its immediate flag-parsing helper are in scope; no reformatting, comment edits, or reordering elsewhere in `bin/cli.js` or `tests/cli.test.js`.

## Acceptance restatement

Verbatim `## Verification` block from `.devlyn/criteria.generated.md`:

```json
{
  "verification_commands": [
    { "cmd": "node bin/cli.js version", "exit_code": 0, "stdout_contains": [], "stdout_not_contains": ["{"] },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":"], "stdout_not_contains": [] },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1, "stdout_contains": [], "stdout_not_contains": [] },
    { "cmd": "npm test", "exit_code": 0, "stdout_contains": [], "stdout_not_contains": [] }
  ]
}
```

Plain-language restatement of every binding behavioral clause from the raw Goal:

1. `node bin/cli.js version --format json` must print valid JSON of the exact shape `{"version":"<x.y.z>"}` on a single line (no pretty-printing, no extra whitespace), where `<x.y.z>` is the version read from `package.json`.
2. `node bin/cli.js version` (no `--format` flag) must keep printing the current bare version string, unchanged — no JSON braces anywhere in stdout.
3. `node bin/cli.js version --format yaml`, and `--format` with any value other than `json` (including missing/empty), must exit with code 1 and print an error (not silently succeed, not silently fall back to bare string).
4. All existing tests in `tests/cli.test.js` (`hello default`, `hello with --name`, `version prints package version`) must keep passing unmodified.
5. At least one new test must be added to `tests/cli.test.js` covering the `--format json` path (asserting valid JSON output with the expected `version` key/value).
6. Only `bin/cli.js` and `tests/cli.test.js` may be modified — no other subcommands, no other files, no new npm dependencies.
7. All code unrelated to the version/`--format` feature — including comments and formatting elsewhere in both files — must remain byte-for-byte as-is; no incidental refactoring or cleanup.
