# Plan — `--format json` for the `version` subcommand

<!-- devlyn:authorized-surface -->
## 1. Files to touch

- `bin/cli.js` — `edit`: add `--format` parsing to the `version` case (Requirements: "Add a `--format json` option to the `version` subcommand"; "`--format yaml` ... must exit with code 1"). Only the `case 'version':` block gains logic; no other line in the file changes.
- `tests/cli.test.js` — `edit`: add new test(s) for `--format json` and `--format yaml` (Requirement: "Add at least one new test in `tests/cli.test.js` covering the `--format json` path"). Existing tests are untouched.

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## 2. Risks

- **Scope creep into `hello`/`parseGreetingFormat`.** The unused `parseGreetingFormat(_argv)` helper (bin/cli.js:29-31) and its TODO comments are a decoy — same-sounding name, but it backs `hello`, not `version`. It stays byte-for-byte unchanged: not called, not renamed, not removed, not even reformatted. A new, separate parsing function for `version --format` will be added instead of reusing/modifying it.
- **Touching unrelated bytes.** Constraint requires the `hello` command, `USAGE` text, and all unrelated comments/formatting stay byte-for-byte identical. The diff must be additive only inside the `version` case (plus one new small helper function and new test code) — no incidental reformatting of surrounding lines.
- **`stdout_not_contains: ["{"]` for bare `version`.** The existing `console.log(readPackageVersion())` path must remain completely unchanged (no wrapping, no trailing text) so plain output never contains `{`.
- **Exact JSON shape.** Verification expects the literal substring `{"version":"0.1.0"}` with no spaces — must use `JSON.stringify({ version })` (which produces no extra whitespace) or an equivalent compact literal, not a hand-built template that could introduce whitespace drift.
- **`--format` value validation.** Only the literal string `json` is valid. Any other value (`yaml`, empty flag with no value, unknown flag value) must print an error to stderr and `process.exit(1)`. Must not throw an uncaught exception (which would also exit non-zero but is not "print an error" in a controlled way, and Node's default uncaught-exception exit code is 1 but stack-trace output is not a clean error message) — use an explicit `console.error` + `process.exit(1)`, mirroring the existing style used by `parseNameFlag`'s `--name requires a value` error and the `Unknown command` default case.
- **Flag parsing scope.** `version` currently takes no arguments. New parsing must only recognize `--format <value>`; it must not accidentally interfere with `hello`'s `--name` parsing (separate command branch, no shared state) and must not add a generic flag-parsing abstraction (no new dependency, no argv library) — a small local function mirroring `parseNameFlag`'s existing pattern in the same file is sufficient and matches "no new dependencies" / no overengineering.
- **No new dependencies.** JSON formatting uses built-in `JSON.stringify`; no argv-parsing library.
- **Test additions must not weaken existing tests.** New tests are appended after the existing `version prints package version` test; none of the three existing tests (`hello default`, `hello with --name`, `version prints package version`) are modified or removed.
- **`node --test tests/` must stay green.** New tests must use the same `run()` helper (execFileSync) already defined in the test file; for the `--format yaml` exit-1 case, `execFileSync` throws on non-zero exit — the test must catch/inspect `error.status` and `error.stderr` (or use the existing test file's established pattern) rather than letting the exception fail the test unexpectedly. Reading the current test file confirms no existing test yet exercises a non-zero exit path, so this is new but minimal test-harness usage, not a new abstraction (execFileSync already accepted for stderr/status inspection via its documented `error.status`/`error.stdout`/`error.stderr` properties on throw).

## 3. Acceptance restatement

```json
{
  "verification_commands": [
    { "cmd": "node bin/cli.js version", "exit_code": 0, "stdout_not_contains": ["{"] },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\"0.1.0\"}"] },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1 },
    { "cmd": "node --test tests/cli.test.js", "exit_code": 0 }
  ]
}
```
