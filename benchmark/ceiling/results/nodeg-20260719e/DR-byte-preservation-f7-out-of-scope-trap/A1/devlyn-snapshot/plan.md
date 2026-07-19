<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` (edit) — inside the existing `case 'version':` block (currently `bin/cli.js:59-62`), parse an optional `--format` flag from `rest` using the same `indexOf`-based pattern already used by `parseNameFlag` (`bin/cli.js:33-42`). No flag → unchanged bare `console.log(readPackageVersion())` (Requirement: "Without `--format` ... keeps printing the current bare version string (unchanged behavior)"). `--format json` → `console.log(JSON.stringify({ version: readPackageVersion() }))`, a single line of valid JSON (Requirement: "output must be a single line of valid JSON: `{"version":"<x.y.z>"}`"). Any other `--format` value → `console.error(...)` + `process.exit(1)`, mirroring the existing error idiom used in `parseNameFlag` (`bin/cli.js:38-39`) and the unknown-command branch (`bin/cli.js:64-66`) (Requirement: "`--format yaml`, or any other unsupported `--format` value, must exit with code `1` and print an error").
- `tests/cli.test.js` (edit) — add a test that runs `version --format json` and asserts the stdout parses as JSON with a `version` field matching `\d+\.\d+\.\d+` (Requirement: "Add at least one new test covering the `--format json` path"), and a test that asserts `version --format yaml` throws via `execFileSync` with a non-zero exit status, to cover the reject-unsupported-format path (Requirement: "`--format yaml` ... must exit with code `1`").

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Out-of-scope expansions to refuse**: do not touch the pre-existing dead-code TODO `parseGreetingFormat` (`bin/cli.js:27-31`); do not touch the `hello` subcommand or its TODO comment (`bin/cli.js:54-58`); do not touch `--help`/`-h` handling; do not modify the `USAGE` string (`bin/cli.js:8-19`) to document `--format json` — no Requirement asks for a help-text update, so adding one is unrequested scope creep. No new files, no new npm dependencies, no refactor of `readPackageVersion` or `parseNameFlag`. Unrelated code, comments, and formatting stay byte-for-byte identical per the criteria's explicit constraint.
- **Ambiguous spec point, resolved strictly**: the criteria say "Without `--format` (or with no format flag)" keeps the bare string, and "any other unsupported `--format` value" exits 1. This leaves `--format` present but with a missing value (e.g. `version --format` at end of argv, or followed by another flag) undefined. Resolve strictly toward the literal read: only an explicit value of exactly `"json"` takes the JSON path; a present-but-missing/invalid value is an "other value" and must exit 1 — it must NOT silently fall back to the bare-string success path (falling back would be a hidden-fallback workaround, forbidden by the no-workaround principle). This mirrors `parseNameFlag`'s existing behavior of erroring rather than silently defaulting when a flag's value is missing.
- **Known failure mode in tests**: `execFileSync` throws (does not return) on a non-zero exit code, so the existing `run()` helper (`tests/cli.test.js:8-10`) cannot be reused as-is for the `--format yaml` rejection test. That test must call `execFileSync`/`run()` inside `assert.throws(...)` (or a try/catch) and assert on the thrown error's `status` property, otherwise the test would falsely fail on an uncaught throw instead of verifying exit code 1.
- **Best practice**: build the JSON output with `JSON.stringify`, not hand-built string concatenation — avoids quoting/escaping bugs and matches the "use standard primitives" principle.

## Acceptance restatement

```json
{
  "verification_commands": [
    { "cmd": "node bin/cli.js version", "expect_type": "stdout_match", "expect": "^\\d+\\.\\d+\\.\\d+$" },
    { "cmd": "node bin/cli.js version --format json", "expect_type": "stdout_match", "expect": "^\\{\"version\":\"\\d+\\.\\d+\\.\\d+\"\\}$" },
    { "cmd": "node bin/cli.js version --format yaml", "expect_type": "exit_code", "expect": "1" },
    { "cmd": "npm test", "expect_type": "exit_code", "expect": "0" }
  ]
}
```
