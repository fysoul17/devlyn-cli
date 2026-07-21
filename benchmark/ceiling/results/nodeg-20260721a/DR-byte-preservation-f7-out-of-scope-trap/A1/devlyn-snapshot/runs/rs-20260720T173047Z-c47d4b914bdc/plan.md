# Plan — `version --format json` support

<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — edit — add a `--format` flag parser and branch the `version` case (bin/cli.js:59-62) to emit `{"version":"<x.y.z>"}` when `--format json` is passed, keep the existing bare `console.log(readPackageVersion())` when no flag is passed, and `console.error(...)` + `process.exit(1)` for any other `--format` value, per Requirements 1-3.
- `tests/cli.test.js` — edit — add at least one new `test(...)` block exercising `node bin/cli.js version --format json` via the existing `run()`/`execFileSync` helper (tests/cli.test.js:8-10), per Requirement 4.

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Scope creep on `parseGreetingFormat`** (bin/cli.js:29-31): unused helper with an explicit TODO marking it out of scope. Do not touch, rename, wire up, or remove it — Requirements/Constraints/Out-of-Scope all name it explicitly.
- **Scope creep on `hello`/`--name`/USAGE banner**: none of these are part of this feature. Leave bin/cli.js:8-19 (USAGE), bin/cli.js:33-42 (`parseNameFlag`), and bin/cli.js:53-58 (`hello` case) byte-identical.
- **New flag-parsing helper vs. inline logic**: `parseNameFlag` (bin/cli.js:33-42) is the existing style precedent — a small top-level function that reads `argv`, returns a value or calls `console.error` + `process.exit(1)`. The new `--format` parsing must follow this same shape (per Constraints: "Follow ... the flag-parsing style of `parseNameFlag`"), not an ad-hoc inline block, to stay idiomatic with the file's existing pattern. This is the one net-new piece of logic the spec requires — no cheaper deletion makes it unnecessary since the feature is genuinely new behavior.
- **Interpreting "any other value not equal to `json`"**: must also cover `--format` with no value / value starting with `-` (mirrors `parseNameFlag`'s existing missing-value guard at bin/cli.js:37-40) and bare `--format` at end of argv. Treat every non-`"json"` outcome (including missing/malformed value) as the error path — exit 1, per Requirement 3. Do not special-case "no --format flag at all" as an error; that must remain the unchanged bare-string path (Requirement 2).
- **JSON output must be single-line and use double quotes**: `JSON.stringify({ version })` — native, no new dependency, matches Constraint "No new npm dependencies."
- **Do not weaken/remove existing tests**: `tests/cli.test.js`'s three existing `test(...)` blocks (lines 12-25) and all of `tests/server.test.js` must keep passing unmodified — only add, don't edit existing test bodies.
- **Ambiguity resolved strictly**: the spec gives the literal error-exit pattern precedent twice (`parseNameFlag` at bin/cli.js:37-40, unknown-command branch at bin/cli.js:63-66) — use `console.error(...)` then `process.exit(1)`, not `throw` or `process.exitCode =`.

## Acceptance restatement

Verbatim from `.devlyn/criteria.generated.md`:

```json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\"0.1.0\"}"] },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1 }
  ]
}
```
