<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — edit — add `--format` flag parsing inside the existing `case 'version':` block (`bin/cli.js:59-62`) so the flag can select JSON output or reject unsupported values. Satisfies Requirements 1–3 (`--format json` prints `{"version":"<x.y.z>"}`; no flag keeps the current bare-string behavior; any other `--format` value exits 1 with an error).
- `tests/cli.test.js` — edit — add a new `test(...)` case (after the existing `version prints package version` test at `tests/cli.test.js:22-25`) that runs `node bin/cli.js version --format json` and asserts the stdout is exactly `{"version":"<x.y.z>"}` (valid single-line JSON). Satisfies Requirement 5 (new test coverage for the `--format json` path) while Requirement 4 (existing tests keep passing) is satisfied by leaving all current tests untouched.

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Refuse to touch `parseGreetingFormat` (`bin/cli.js:29-31`).** It is unused, unrelated to `version`, and explicitly called out in the criteria's Out of Scope list — leave it byte-for-byte as-is even though it looks like a natural home for "format" parsing logic.
- **Refuse to touch the `hello` command, `--help`/`USAGE` text, or any other file.** Criteria's Out of Scope section and the user's explicit "Only touch bin/cli.js and tests/cli.test.js" both forbid it. In particular, do not update `USAGE` to mention `--format` — that's unrequested scope expansion (the acceptance criteria never asks for `--help` text to change), even though it would look "more complete."
- **No new named helper function for `--format` parsing.** Unlike `parseNameFlag`, the `--format` logic only needs to run inside `case 'version':` once; inlining it there is the smaller diff and avoids adding a second flag-parsing abstraction that isn't asked for (subtractive-first / no-overengineering — a new helper needs a cited failure mode this repo doesn't have).
- **Strict reading of "or any other unsupported value" (Requirement 3):** this must also cover `--format` supplied with no value at all (e.g. `version --format` with nothing after it, or `--format` as the last arg). Any `--format` occurrence whose value is not the literal string `json` triggers the exit-1 error path. Only the total absence of `--format` preserves the legacy bare-string behavior.
- **Literal output match:** `console.log(JSON.stringify({ version: readPackageVersion() }))` produces exactly `{"version":"0.1.0"}` (compact `JSON.stringify` with a single key, no extra whitespace) plus the newline `console.log` always appends — matches the required single-line JSON literal and the verification command's `stdout_contains` check.
- **Error path plumbing:** follow the file's existing error convention (`console.error(...)` then `process.exit(1)`, as already used in `parseNameFlag` at `bin/cli.js:38-39` and the `default` case at `bin/cli.js:64-66`) rather than throwing or introducing a different error-reporting mechanism.
- **Test-runner exit-code gotcha:** `execFileSync` (used by the existing `run()` helper in `tests/cli.test.js:8-10`) throws on non-zero exit. Requirement 5 only asks for a test of the `--format json` success path (exit 0), so the new test can reuse `run()` unmodified — do not add an exit-1/`--format yaml` test to `tests/cli.test.js`, since that isn't requested and the yaml-exit-1 behavior is already covered by the standalone verification command (`node bin/cli.js version --format yaml`), not by `npm test`.
- **No new npm dependencies** — `JSON.stringify` is a language builtin; nothing to add to `package.json` (which is not in the authorized surface anyway).

## Acceptance restatement

## Verification
```json
{
  "verification_commands": [
    { "cmd": "node bin/cli.js version", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\"0.1.0\"}"] },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1 },
    { "cmd": "npm test", "exit_code": 0 }
  ]
}
```
