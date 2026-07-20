<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — edit: replace the body of the `case 'version':` block (currently `bin/cli.js:59-62`, `console.log(readPackageVersion()); return;`) to parse a `--format` flag from `rest` and branch: no flag → unchanged bare-version print (Requirement: "Without `--format` ... `version` keeps printing the current bare version string, unchanged"); `--format json` → `console.log(JSON.stringify({ version: readPackageVersion() }))` (Requirement: "print a single-line, valid JSON object `{\"version\":\"<x.y.z>\"}`"); any other `--format` value (including a missing value) → `console.error(...)` + `process.exit(1)` (Requirement: "`--format yaml` (or any other unsupported `--format` value) exits with code 1 and prints an error").
- `tests/cli.test.js` — edit: add new `test(...)` block(s) after the existing `version prints package version` test (`tests/cli.test.js:22-25`) covering `version --format json` (parse stdout with `JSON.parse`, assert `.version` matches `/^\d+\.\d+\.\d+$/`) and `version --format yaml` (assert non-zero/1 exit via try/catch around `execFileSync`, since the existing `run()` helper at `tests/cli.test.js:8-10` throws on non-zero exit and is reused, not modified) (Requirement: "Add at least one new test in `tests/cli.test.js` covering the `--format json` path"; Requirement: "Existing tests in `tests/cli.test.js` keep passing").

No other files are touched. No new top-level helper function is added — the `--format` parsing is inlined in the `version` case body, which is the smallest change that satisfies the requirement (`parseNameFlag` is not reused because its error/return contract — printing a fixed "requires a value" message and defaulting on missing value — does not match the "any unsupported value including missing exits 1" contract needed here; introducing a second near-duplicate helper would be pure accretion for a 6-line branch used in exactly one place).

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Out-of-scope expansions to refuse**: do not touch `hello`, `parseGreetingFormat` (line 27-31, explicitly called out in criteria as "leave as-is"), `parseNameFlag`, `USAGE` text, or any comment/formatting outside the `version` case body and the new test(s). Do not add a package like `js-yaml` to make `--format yaml` "actually work" — the spec requires yaml to be rejected, not supported. Do not create new files (no new test fixtures, no new lib module for format-parsing).
- **Ambiguous spec sections, resolved strictly**:
  - `version --format` with no trailing value (dangling flag): criteria says "any other unsupported `--format` value" — a missing value is not `"json"`, so it exits 1. Handled naturally since `rest[formatIdx + 1]` is `undefined` and `undefined !== 'json'`.
  - Flag position: `--format` is located via `indexOf` anywhere in `rest` (mirrors existing `parseNameFlag` convention at `bin/cli.js:33-42`), not required to be the first token — consistent with how `--name` is parsed for `hello`.
  - JSON output must be "single-line" — `JSON.stringify({ version })` with no indentation argument produces a single line; `console.log` appends exactly one trailing `\n`, which does not violate "single-line" (it's the line terminator, not a second line) and does not break `JSON.parse` (JSON grammar permits insignificant trailing whitespace).
- **Known failure modes for this language/framework**:
  - Forgetting `return` after the new branches would fall through to nothing else (switch has no other cases after `version`), but omitting `return` after `process.exit(1)` is moot (exit terminates immediately) — still include `return`/exit consistently to match existing style in the file (`hello` and current `version` both `return` after their `console.log`).
  - `tests/cli.test.js`'s `run()` helper (`execFileSync` with default behavior) throws on non-zero exit code — the new "unsupported format" test must wrap the call in `try/catch` (or use `execFileSync` directly with a local try/catch) rather than reusing `run()` unguarded, otherwise the test itself throws and fails for the wrong reason.
  - `readPackageVersion()` reads `package.json` fresh on each call — no caching/staleness risk to account for.

## Acceptance restatement

```json
{
  "verification_commands": [
    {
      "cmd": "node bin/cli.js version",
      "exit_code": 0,
      "stdout_contains": ["0.1.0"],
      "stdout_not_contains": ["{"]
    },
    {
      "cmd": "node bin/cli.js version --format json",
      "exit_code": 0,
      "stdout_contains": ["{\"version\":\"0.1.0\"}"]
    },
    {
      "cmd": "node bin/cli.js version --format yaml",
      "exit_code": 1
    },
    {
      "cmd": "node --test tests/",
      "exit_code": 0
    }
  ]
}
```
