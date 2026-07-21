# Plan — `--format json` for `version` subcommand

<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — edit — add `--format` flag parsing plus a JSON output branch inside the existing `case 'version':` block (`bin/cli.js:59-62`). Bare `version` (no flag) must keep calling `console.log(readPackageVersion())` unchanged (Requirement 1). `--format json` prints `` {"version":"<x.y.z>"} `` built from the existing `readPackageVersion()` (`bin/cli.js:21-25`) via `JSON.stringify` (Requirement 2). Any other `--format` value prints an error and `process.exit(1)`, mirroring the existing `--name`-missing-value error pattern at `bin/cli.js:37-40` (Requirement 3).
- `tests/cli.test.js` — edit — add new test(s) after the existing `'version prints package version'` test (`tests/cli.test.js:22-25`): one asserting `--format json` stdout is exactly `` {"version":"x.y.z"} `` (parseable via `JSON.parse`), and one asserting `--format yaml` (or another unsupported value) causes the CLI to exit 1 — this second test must wrap the `run()` call in `try/catch` (or otherwise capture the thrown error), since `run()` uses `execFileSync`, which throws on non-zero exit rather than returning (Requirement 4, Constraint on `execFileSync`).

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Refuse scope creep into `hello`.** `parseGreetingFormat` (`bin/cli.js:27-31`, already dead/unused) and `parseNameFlag` (`bin/cli.js:33-42`) are Out of Scope per the spec — do not touch, "fix," or remove them even though `parseGreetingFormat` is visibly dead code. Mention only if asked; do not delete (Goal-locked rule 1).
- **Refuse dispatch refactor.** The `switch (command)` structure in `main()` (`bin/cli.js:44-68`) stays as-is beyond the minimum `--format` parsing added inside the `version` case. No restructuring of command dispatch (Out of Scope, spec line 21).
- **USAGE text left untouched.** No Requirement or verification command checks `--help`/`USAGE` output for a `--format` mention; adding one would be an unrequested addition (Core principle 2, no-overengineering / Goal-locked rule 1). `USAGE` (`bin/cli.js:8-19`) stays byte-for-byte identical.
- **Byte-for-byte constraint is strict.** The two `TODO` comments (`bin/cli.js:27-28`, `bin/cli.js:54`) and all code outside the `version` case must not shift — no incidental reformatting, reindentation, or reordering of unrelated lines. Only the `version` case body (and a new small helper, see below) may change.
- **New helper is justified, not extra.** Parsing `--format` needs a small helper analogous to `parseNameFlag` (`bin/cli.js:33-42`) — this is the existing idiom in this file (best practice: consistency with established pattern), not a novel abstraction. Keep it minimal: read the flag, validate against the single accepted value `json`, else error + exit 1. Do not generalize it into a reusable multi-flag parser — no other command needs one.
- **Ambiguous case: `--format` with no trailing value.** The spec's Requirements only enumerate "no flag" / "`--format json`" / "`--format yaml` (or other unsupported value)". A bare trailing `--format` with nothing after it is not explicitly named. Resolution: treat a missing/absent value the same as an unsupported value (error + exit 1) rather than adding a distinct third error branch — this satisfies "any other unsupported `--format` value" literally (an absent value is not the supported `json` value) without inventing new observable behavior the spec never described.
- **Reuse `readPackageVersion()` for both output paths** (`bin/cli.js:21-25`) — do not duplicate the `fs.readFileSync`/`JSON.parse` logic for the JSON-output branch. Same source of truth for both the bare string and the JSON payload keeps the two paths from drifting.
- **No new dependencies.** JSON encoding uses the built-in `JSON.stringify` only (Constraint, spec line 13).
- **Test error-path failure mode.** Forgetting the `try/catch` around the unsupported-format test's `run()` call will make that test itself throw and fail with an uncaught exception rather than asserting the intended exit-1 behavior — this is the specific failure mode the spec's `execFileSync` constraint (spec line 15) warns about.
- **Exact stdout matching.** The verification command checks `stdout_contains: ["{\"version\":\"0.1.0\"}"]` — `JSON.stringify({ version })` naturally produces this compact, no-space form; do not add `JSON.stringify(obj, null, 2)`-style pretty-printing, which would break the substring match.

## Acceptance restatement

Verbatim from `.devlyn/criteria.generated.md`:

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "npm test", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\"0.1.0\"}"] },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1 }
  ]
}
```
