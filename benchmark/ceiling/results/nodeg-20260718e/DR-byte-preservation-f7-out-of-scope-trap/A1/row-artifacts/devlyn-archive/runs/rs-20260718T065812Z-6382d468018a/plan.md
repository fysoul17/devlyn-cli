# Plan — `--format json` for the `version` subcommand

<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — `edit`: add `--format` parsing for the `version` case (Requirement: "Add a `--format json` option to the `version` subcommand ... valid JSON on a single line"; "Without `--format json`, keep current behavior"; "`--format yaml` or unsupported value exits 1 with an error").
- `tests/cli.test.js` — `edit`: add new test(s) for `version --format json` success and `version --format <unsupported>` failure (Requirement: "gains at least one new test covering the `--format json` path"; "All existing tests ... continue to pass").

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Out-of-scope expansion to refuse**: do not touch `hello`, `--help`/`-h`, `USAGE`, `parseNameFlag`, `parseGreetingFormat` (explicitly marked dead/out-of-scope by its own comment at bin/cli.js:27-31), `package.json`, or any file outside the authorized surface. Do not "clean up" the unused `parseGreetingFormat` helper — pre-existing, out of scope, mention-only per contract.
- **Byte-for-byte preservation**: all existing lines in `bin/cli.js` and `tests/cli.test.js` outside the new `version` logic/tests must remain untouched — no reflow, no comment edits, no reformatting of surrounding code. New code must be inserted, not interleaved with edits to unrelated lines.
- **Ambiguous spec point — resolve strictly**: "any other unsupported `--format` value" must exit 1 with an error (via `console.error` + `process.exit(1)`, matching the existing `parseNameFlag` error pattern at bin/cli.js:37-40 and the `default:` unknown-command pattern at bin/cli.js:63-66). This includes `--format` with no value, `--format yaml`, `--format ""`, etc. — anything other than exactly `json`.
- **JSON output shape is literal**: must be exactly `{"version":"<x.y.z>"}` (no spaces, single line) — use `JSON.stringify({ version: readPackageVersion() })`, do not hand-build the string, to guarantee correct escaping and match `stdout_contains: ["{\"version\":\""]`.
- **No new dependencies**: use only `JSON.stringify` (built-in) — do not add a YAML/JSON library.
- **Argv parsing scope**: `--format` must be parsed only from the `version` command's `rest` args, mirroring the existing pattern of `parseNameFlag(rest)` for `hello`. Do not introduce a global/shared flag parser beyond what's needed (subtractive-first: reuse the existing `indexOf`-based flag-parsing idiom already used by `parseNameFlag` rather than adding a new abstraction).
- **Test isolation**: `execFileSync` throws on non-zero exit (existing helper `run()` at tests/cli.test.js:8-10 does not catch); the new failure-path test must invoke the CLI in a way that captures the non-zero exit (e.g. wrap in `assert.throws` or use a helper that catches and inspects `error.status`/`error.stdout`/`error.stderr`), without modifying the existing `run()` helper's behavior for other tests.

## Acceptance restatement

Verbatim from `.devlyn/criteria.generated.md`:

```json
{
  "verification_commands": [
    { "cmd": "node bin/cli.js version", "exit_code": 0, "stdout_contains": [] },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\""] },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1 },
    { "cmd": "node --test tests/", "exit_code": 0 }
  ]
}
```

Requirements (verbatim from criteria):

- Add a `--format json` option to the `version` subcommand in `bin/cli.js`. With the flag, output must be valid JSON on a single line: `{"version":"<x.y.z>"}` where `<x.y.z>` is the value from `package.json`.
- Without `--format json`, the `version` subcommand keeps its current behavior: print the bare version string (unchanged).
- `--format yaml`, or any other unsupported `--format` value, exits with code 1 and prints an error (does not print a version).
- All existing tests in `tests/cli.test.js` continue to pass.
- `tests/cli.test.js` gains at least one new test covering the `--format json` path.

Constraints (verbatim from criteria):

- Touch only `bin/cli.js` and `tests/cli.test.js`. No other files.
- Do not modify the `hello` subcommand, `--help`/`-h`, or any other existing subcommand behavior.
- No new npm dependencies (`package.json` dependencies/devDependencies unchanged).
- Code unrelated to the `--format` feature — including existing comments and formatting in `bin/cli.js` and `tests/cli.test.js` — must remain byte-for-byte as-is. No unrelated refactor or cleanup.
</content>
