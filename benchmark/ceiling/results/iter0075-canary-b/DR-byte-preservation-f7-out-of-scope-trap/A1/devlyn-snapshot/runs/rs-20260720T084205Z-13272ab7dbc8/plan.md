# Plan — add `--format json` to `version` subcommand

<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` (edit) — insert a `parseFormatFlag(argv)` helper mirroring the existing `parseNameFlag` precedent (`bin/cli.js:33-42`: read the flag's value, `console.error` + `process.exit(1)` on anything unsupported), and change the `case 'version':` block (`bin/cli.js:59-62`) to call it and branch between `console.log(JSON.stringify({ version }))` and the current `console.log(version)`. Satisfies Requirements 1–3 (JSON output shape, unchanged bare-string default, exit-1 rejection of unsupported `--format` values).
- `tests/cli.test.js` (edit) — add one new `test(...)` block after the existing `version prints package version` test (`tests/cli.test.js:22-25`) that runs `run(['version', '--format', 'json'])` and asserts the stdout is valid JSON matching `{"version": "<x.y.z>"}`. Satisfies Requirement 5 (new-test coverage for the `--format json` path). No other test files change.

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **USAGE block is explicitly out of scope.** `.devlyn/criteria.generated.md` lists "Refactoring or cleanup of ... USAGE" under Out of Scope, and the goal says unrelated formatting/comments must stay byte-for-byte identical. `bin/cli.js:8-19` (the `USAGE` template literal) is NOT touched even though it currently omits `--format json` from the `version` command's documented options — refuse the temptation to "helpfully" document the new flag there.
- **Do not touch the unused `parseGreetingFormat` helper** (`bin/cli.js:29-31`) or either `TODO` comment (`bin/cli.js:27-28`, `bin/cli.js:54`). These are explicitly called out in criteria as must-remain-as-is. The new helper must be named distinctly (`parseFormatFlag`, not `parseGreetingFormat`) so it is obviously unrelated to the dead code.
- **Do not touch `hello`, `parseNameFlag`, the unknown-command branch, or any file outside `bin/cli.js` / `tests/cli.test.js`** — no changes to `package.json`, `package-lock.json`, `README.md`, `server/index.js`, `web/index.html`, `playwright.config.js`, or `tests/server.test.js`. No new dependency: `--format json` needs only `JSON.stringify`, already a global.
- **Exact JSON shape.** Requirement is a single line `{"version":"<x.y.z>"}` with no extra whitespace/indentation and no trailing content besides the newline `console.log` appends. Use `JSON.stringify({ version })` (no space/indent args) — matches the verification script's `JSON.stringify({version:pkg.version})+'\n'` byte-for-byte. Do not hand-build the JSON string with template literals, since that risks quoting/escaping bugs `JSON.stringify` already handles correctly (best-practice: use the standard primitive, not a hand-rolled encoder).
- **Unsupported-value handling covers the missing-value case too.** "`--format yaml` (or any other unsupported value)" must exit 1. Treat any value that is not exactly `'json'` — including `--format` with no following value (`undefined`) — as unsupported, consistent with how `parseNameFlag` already treats a missing/absent value as invalid. Do not special-case a distinct error message per bad value; one `console.error` + `process.exit(1)`, matching the existing `parseNameFlag` pattern, is sufficient and avoids inventing new error-formatting conventions.
- **Test-scope discipline.** The goal and criteria require only "at least one" new test, specifically for the `--format json` path. The `--format yaml`-rejection and unchanged-bare-version behaviors are already covered by the pipeline's own mechanical verification commands (ad hoc `node -e` scripts, not `tests/cli.test.js`). Adding extra unit tests for those paths is not requested and is not required to satisfy any Requirement bullet — per Goal-locked execution, only the one requested test is added; do not pad `tests/cli.test.js` with additional yaml/bare-version test cases.
- **Preserve existing test file structure and style.** New test goes in `tests/cli.test.js` using the same `test(...)`/`assert.*` idioms and the existing `run()` helper already in the file (`tests/cli.test.js:8-10`) — no new test utilities, no new imports.

## Acceptance restatement

Verbatim from `.devlyn/criteria.generated.md`:

```json
{
  "verification_commands": [
    {
      "cmd": "node -e \"const {execFileSync}=require('child_process'); const pkg=require('./package.json'); const out=execFileSync('node',['bin/cli.js','version','--format','json'],{encoding:'utf8'}); const expected=JSON.stringify({version:pkg.version})+'\\n'; if(out!==expected){console.error('mismatch: '+JSON.stringify(out)); process.exit(1);} console.log('FORMAT_JSON_OK');\"",
      "exit_code": 0,
      "stdout_contains": ["FORMAT_JSON_OK"],
      "stdout_not_contains": []
    },
    {
      "cmd": "node -e \"const {execFileSync}=require('child_process'); const out=execFileSync('node',['bin/cli.js','version'],{encoding:'utf8'}); if(!/^\\d+\\.\\d+\\.\\d+\\n$/.test(out)){console.error('mismatch: '+JSON.stringify(out)); process.exit(1);} console.log('BARE_VERSION_OK');\"",
      "exit_code": 0,
      "stdout_contains": ["BARE_VERSION_OK"],
      "stdout_not_contains": []
    },
    {
      "cmd": "node -e \"const {execFileSync}=require('child_process'); try { execFileSync('node',['bin/cli.js','version','--format','yaml'],{encoding:'utf8'}); console.error('expected nonzero exit'); process.exit(1); } catch(e){ if(e.status!==1){console.error('wrong exit code: '+e.status); process.exit(1);} console.log('FORMAT_YAML_REJECTED'); }\"",
      "exit_code": 0,
      "stdout_contains": ["FORMAT_YAML_REJECTED"],
      "stdout_not_contains": []
    },
    {
      "cmd": "npm test",
      "exit_code": 0,
      "stdout_contains": [],
      "stdout_not_contains": ["not ok"]
    }
  ]
}
```
