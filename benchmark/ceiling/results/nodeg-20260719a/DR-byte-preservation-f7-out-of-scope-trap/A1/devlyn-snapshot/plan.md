<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — `edit` — add `--format json` support to the `version` case (Requirement: "`bin/cli.js version --format json` prints exactly one line of valid JSON"; Requirement: "`version` with no `--format` flag keeps printing the bare version string ... unchanged"; Requirement: "`--format yaml` (or any other unsupported `--format` value) exits with status code 1 and prints an error").
- `tests/cli.test.js` — `edit` — add tests covering the `--format json` path and the `--format yaml` error path (Requirement: "`tests/cli.test.js` gains at least one new test covering the `--format json` path").

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Refuse USAGE-text drift.** The `USAGE` banner (`bin/cli.js:8-19`) documents `version` without `--format`. Spec does not ask for a help-text update; do not touch `USAGE` — that would be unrequested/tangential work outside the two-file, feature-only scope.
- **Refuse touching `hello` or `parseGreetingFormat`.** `bin/cli.js:29-31` has an explicitly-marked dead helper (`// TODO(devlyn): ... leftover from an abandoned refactor ... out of scope`) and `bin/cli.js:53-58` (`hello`) has its own out-of-scope TODO. Both are pre-existing dead/unrelated code — mention only, do not delete or "helpfully" wire up, per Out of Scope.
- **Missing-value strictness.** `version --format` with nothing following it (`rest[idx+1] === undefined`) is not `'json'`, so it must fall into the same exit-1 error path as `--format yaml` — no special-cased message, no silent default to bare output. This mirrors the existing `parseNameFlag` (`bin/cli.js:33-42`) convention of validating and calling `process.exit(1)` inside the parser rather than in the switch body.
- **Single-line JSON.** Must use `JSON.stringify({ version })` (no `null, 2` indentation argument) — indentation would break the "single line" and literal `{"version":"<x.y.z>"}` requirement.
- **No new abstraction.** Reuse the existing `parseNameFlag`-style parse-and-validate-inline pattern for a new `parseFormatFlag(argv)` helper rather than inventing a different validation shape — stays idiomatic with the rest of the file.
- **Test-exit-code capture.** `execFileSync` (already imported in `tests/cli.test.js:3`) throws on non-zero exit; the new exit-1 test must `assert.throws` and check `err.status === 1` rather than using the existing `run()` helper (`tests/cli.test.js:8-10`), which assumes success and returns stdout only.
- **No hardcoded version literal in new tests.** Existing `version prints package version` test (`tests/cli.test.js:22-25`) asserts via `/\d+\.\d+\.\d+/` regex, not a literal `"0.1.0"`, to avoid drifting from `package.json`. The new `--format json` test follows the same convention: regex-match the JSON shape rather than hardcode the version string.
- **No new dependencies, no other files.** `package.json` (`dependencies`/`devDependencies`) stays untouched; only `bin/cli.js` and `tests/cli.test.js` are in the authorized surface.

## Acceptance restatement

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
