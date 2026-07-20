# Plan — `version --format json` flag

<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` (edit) — in the `case 'version':` block (bin/cli.js:59-62), parse a new `--format` flag: no flag → keep existing `console.log(readPackageVersion())` bare-string behavior (Requirement: "Without `--format` ... keeps its current behavior"); `--format json` → print a single line of valid JSON `{"version":"<x.y.z>"}` and exit 0 (Requirement: "accepts a `--format json` flag ... prints a single line of valid JSON"); any other `--format` value → exit code 1 with an error printed, no successful version output (Requirement: "Passing `--format yaml`, or any other value not equal to `json`, exits with code 1"). Add one small helper (mirroring the existing `parseNameFlag` pattern at bin/cli.js:33-42) to read the `--format` value from argv; no other line in the file changes.
- `tests/cli.test.js` (edit) — add at least one new `test(...)` exercising `node bin/cli.js version --format json` and asserting the exact JSON output (Requirement: "At least one new test is added to `tests/cli.test.js` exercising the `--format json` path"). Existing tests (`hello default`, `hello with --name`, `version prints package version`) are left untouched (Requirement: "All existing tests in `tests/cli.test.js` continue to pass").

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Byte-for-byte constraint outside the touched lines.** The `hello` command (bin/cli.js:53-58), `parseNameFlag` (bin/cli.js:33-42), the unused `parseGreetingFormat` helper and its TODO comment (bin/cli.js:27-31), the `TODO: consider supporting a --greeting flag` comment (bin/cli.js:54), the `USAGE` text (bin/cli.js:8-19), and all other formatting/comments must remain byte-for-byte identical. Refuse any temptation to "clean up" `parseGreetingFormat` — it is explicitly out of scope per the generated criteria and the repo's subtractive-first rule does not license touching code the task doesn't require.
- **Refuse scope creep to other subcommands.** Do not add `--format` to `hello` or any other command; do not touch `--help` output. Out of Scope explicitly lists both.
- **No new dependencies / no package.json edit.** JSON output must be built with `JSON.stringify`, not a new dependency; `package.json` is not in the authorized surface and must not change.
- **Exact JSON shape.** `JSON.stringify({ version: readPackageVersion() })` yields `{"version":"0.1.0"}` with no whitespace — matches the required literal `{"version":"<x.y.z>"}` and the verification's `stdout_contains` check. Do not pretty-print or reorder keys.
- **Ambiguous case: `--format` given with no following value or with an empty/missing argument.** The spec only states behavior for "no `--format`" and "`--format json`" vs "`--format <anything-else>`". Interpreting strictly: a `--format` flag present with any value that is not literally `"json"` (including `undefined`/missing) falls into the "any other value not equal to `json`" bucket → exit 1 with an error message. This is the strict reading of the existing requirement text, not a new behavior invented beyond it.
- **Exit-code discipline.** Bare `version` and `--format json` must exit 0 (implicit, by returning normally without `process.exit`); invalid `--format` must call `process.exit(1)` after printing an error to stderr, consistent with the existing `parseNameFlag` error-handling pattern (bin/cli.js:37-40) and the `default:` unknown-command branch (bin/cli.js:63-66).
- **Test isolation.** New test(s) must use the existing `run(args)` helper (tests/cli.test.js:8-10) and existing `assert` module already imported; no new test utilities or dependencies.

## Acceptance restatement

```json
{
  "verification_commands": [
    {
      "cmd": "node --test tests/",
      "exit_code": 0
    },
    {
      "cmd": "node bin/cli.js version",
      "exit_code": 0,
      "stdout_contains": ["0.1.0"],
      "stdout_not_contains": ["{\"version\""]
    },
    {
      "cmd": "node bin/cli.js version --format json",
      "exit_code": 0,
      "stdout_contains": ["{\"version\":\"0.1.0\"}"]
    },
    {
      "cmd": "node bin/cli.js version --format yaml",
      "exit_code": 1
    }
  ]
}
```
