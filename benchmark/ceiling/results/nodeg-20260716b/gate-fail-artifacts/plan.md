<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — edit — the `version` case in the `main()` switch (currently `bin/cli.js:59-62`, `console.log(readPackageVersion())` only) must branch on a `--format` flag read from `rest`: no flag → unchanged bare-string behavior (Requirement: "Without `--format`, the `version` subcommand keeps its current behavior"); `--format json` → emit single-line JSON via `JSON.stringify` reusing the existing `readPackageVersion()` helper (`bin/cli.js:21-25`) (Requirement: "Add a `--format json` option... stdout must be valid single-line JSON"); any other `--format` value (including `yaml` or a missing value) → `console.error` + `process.exit(1)`, mirroring the existing error pattern in `parseNameFlag` (`bin/cli.js:37-40`) (Requirement: "`--format yaml`, or any other unsupported `--format` value, exits with code 1 and prints an error").
- `tests/cli.test.js` — edit — add one new `test(...)` covering the `--format json` path: run `['version', '--format', 'json']` via the existing `run()` helper (`tests/cli.test.js:8-10`), then assert the output is valid JSON with shape `{ version: '<x.y.z>' }` (e.g. `JSON.parse(out)` + `assert.match` on `.version` against `/^\d+\.\d+\.\d+$/`) (Requirement: "Add at least one new test in `tests/cli.test.js` covering the `--format json` path").

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Out-of-scope surfaces to refuse touching**: the `hello` case (`bin/cli.js:53-58`), `parseGreetingFormat` (`bin/cli.js:29-31`, explicitly called out as pre-existing dead code — do not remove or wire up), `parseNameFlag` (`bin/cli.js:33-42`, reuse the *pattern*, do not modify the function itself), `USAGE` (`bin/cli.js:8-19`), the `--help`/`-h`/unknown-command branches (`bin/cli.js:47-50`, `63-66`), and `package.json`, `server/`, `scripts/` (Constraint: "Only `bin/cli.js` and `tests/cli.test.js` may be touched"). Any edit outside the `version` case body and the new test is a violation.
- **No `--format` on other commands**: the flag is scoped to `version` only (Out of Scope: "Adding a `--format` option to any command other than `version`") — do not touch `hello`'s argument parsing.
- **Missing-value edge case must error, not silently fall back to bare output**: `rest.indexOf('--format')` returning a present index but `rest[idx + 1]` being `undefined` (flag is last arg, e.g. `version --format`) must NOT be treated as "no flag" (which would silently produce the bare-string success path). Detect flag-presence separately from flag-value, and route "present but value is not `json`" (including `undefined`) into the same unsupported-format error branch as `yaml`. Conflating "absent" and "present-without-value" would be a silent fallback, which the repo's error-handling contract forbids.
- **No new abstraction required**: `--format` parsing is used exactly once (inside the `version` case), so inline `indexOf`/branch logic is sufficient — do not add a new top-level `parseFormatFlag` function; the existing `parseNameFlag` is a style reference for the error-exit pattern (`console.error` + `process.exit(1)`), not a mandate to extract a matching helper. "No new abstractions unless required for the single new flag" (Constraint).
- **Literal output shape**: JSON success output must be exactly `{"version":"<x.y.z>"}` — a single-key object, so `JSON.stringify({ version: readPackageVersion() })` produces this with no extra whitespace and no key-ordering ambiguity (only one key exists). Do not pretty-print (no indent argument to `JSON.stringify`).
- **Trailing newline is safe**: `console.log` appends `\n`, matching the verification regexes (`^\{\"version\":\"\d+\.\d+\.\d+\"\}\n?$` and `^\d+\.\d+\.\d+\n?$`, both tolerate an optional trailing newline). Use `console.log` for both the bare and JSON success paths, consistent with existing style (`console.log`/`console.error`/`process.exit` for errors — Constraint).
- **Existing test must keep passing unmodified**: `tests/cli.test.js:22-25` (`version prints package version`, regex `/\d+\.\d+\.\d+/` against `run(['version'])`) exercises the no-flag path — the new branch logic must leave that path's exact output untouched.
- **New test must not alter the shared `run` helper**: `run()` (`tests/cli.test.js:8-10`) uses `execFileSync`, which throws on non-zero exit; the required new test only exercises the exit-0 `--format json` success path, so it can call `run()` unmodified. Do not change `run()`'s signature or error-swallowing behavior to accommodate the new test — that would risk changing behavior for the two existing tests. (The `--format yaml` exit-1 case is covered by the pipeline's mechanical `verification_commands`, not a Requirement-5-mandated unit test — do not add extra tests beyond the one required for the json path; that would be unrequested work.)
- **No new dependencies**: use built-in `JSON.stringify`/`JSON.parse` only (Constraint: "No new npm dependencies").
- **Byte-for-byte elsewhere**: all comments, formatting, and whitespace outside the `version` case and the new test must remain identical to current `bin/cli.js` / `tests/cli.test.js` (Constraint).

## Acceptance restatement

## Verification

```json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "expect_exit": 0 },
    { "cmd": "node bin/cli.js version --format json", "expect_exit": 0, "expect_stdout_regex": "^\\{\"version\":\"\\d+\\.\\d+\\.\\d+\"\\}\\n?$" },
    { "cmd": "node bin/cli.js version", "expect_exit": 0, "expect_stdout_regex": "^\\d+\\.\\d+\\.\\d+\\n?$" },
    { "cmd": "node bin/cli.js version --format yaml", "expect_exit": 1 }
  ]
}
```
