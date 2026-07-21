# Plan — `--format json` for the `version` subcommand

<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — edit — add `--format` parsing for the `version` case only (Requirement: "accepts a `--format json` flag" / "unsupported `--format` value ... exit code 1"). All other lines (USAGE, `hello` case, `--help`/`-h`, `parseGreetingFormat`, its TODO comments) stay byte-for-byte identical (Constraint: "Code unrelated to the version feature ... must remain byte-for-byte as-is").
- `tests/cli.test.js` — edit — add new `node:test` case(s) covering the `--format json` path (Requirement: "At least one new test ... covers the `--format json` path"). Existing three tests (`hello default`, `hello with --name`, `version prints package version`) are untouched (Requirement: "All existing tests ... continue to pass").

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Out-of-scope expansions to refuse**: touching `hello`, `--help`/`-h`, or `USAGE`; deleting or "cleaning up" the unused `parseGreetingFormat` helper (`bin/cli.js:29-31`) or its TODO comments (`bin/cli.js:27-28`, `bin/cli.js:54`); adding npm dependencies; reformatting untouched lines; refactoring `readPackageVersion` (`bin/cli.js:21-25`). Criteria explicitly lists `parseGreetingFormat` cleanup as Out of Scope — do not touch it even though it sits adjacent to the edit.
- **Strict interpretation of "unsupported `--format` value"**: this covers (a) any value other than `json` (e.g. `yaml`), and (b) `--format` supplied with no following value / followed by another flag — both must exit 1 with an error message on stderr, never print the bare version or JSON. Mirror the existing `parseNameFlag` (`bin/cli.js:33-42`) convention: `console.error(...)` then `process.exit(1)`, using `indexOf('--format')` (first occurrence) for consistency with `parseNameFlag`'s pattern — no `--format=value` equals-sign syntax, since no flag in this file supports that syntax today and the criteria does not request it.
- **Literal output contract**: with `--format json`, stdout must be exactly one line of valid JSON: `{"version":"<x.y.z>"}` — i.e. `console.log(JSON.stringify({ version: readPackageVersion() }))`, no extra whitespace, no additional keys. Without `--format`, stdout stays exactly `console.log(readPackageVersion())` as today — no wrapping, no behavior change for the plain path.
- **Test scope discipline**: add the required `--format json` test, and it is reasonable to also add one test for the `--format yaml` (or other unsupported value) exit-1 path since that is explicit Requirement 3 text already exercised by the verification commands, not speculative robustness. Do not add tests beyond what Requirements 1–3 describe (e.g. no tests for `--format=value` syntax, no tests for other subcommands' formats — both are explicitly Out of Scope). `execFileSync` throws on non-zero exit with `.status`/`.stderr` populated (default `stdio: 'pipe'`) — the new error-path test must catch that thrown error rather than expect a return value.
- **Known Node CLI parsing failure mode**: `rest[idx + 1]` can be `undefined` or another flag (e.g. `version --format --name`) — must not `throw`/crash uncaught; must be treated as unsupported and exit 1 explicitly (same failure mode `parseNameFlag` already guards against for `--name`).

## Acceptance restatement

```json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["\"version\":"] },
    { "cmd": "node bin/cli.js version", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1 }
  ]
}
```
