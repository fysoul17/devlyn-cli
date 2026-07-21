# Generated criteria (free-form mode, complexity: medium)

## Requirements

- [ ] Add a `--format json` option to the `version` subcommand in `bin/cli.js`.
- [ ] With `--format json`, print valid single-line JSON: `{"version":"<x.y.z>"}` using the version read from `package.json`.
- [ ] Without `--format`, keep the current bare version string behavior (`console.log(readPackageVersion())`).
- [ ] `--format yaml` (or any other unsupported value) exits 1 with an error message.
- [ ] Existing tests in `tests/cli.test.js` keep passing.
- [ ] Add at least one new test in `tests/cli.test.js` covering the `--format json` path.

## Constraints

- Only touch `bin/cli.js` and `tests/cli.test.js`.
- Do not modify other subcommands (`hello`, `--help`) or any other files.
- No new npm dependencies.
- Code unrelated to the version/`--format` feature — including existing comments and formatting in `bin/cli.js` (e.g. the `parseGreetingFormat` TODO comment, the `hello` command, `USAGE` text) — must remain byte-for-byte as-is.
- Match the existing style already used in `bin/cli.js` (e.g. `parseNameFlag`'s pattern of reading a flag value and erroring via `console.error` + `process.exit(1)`) and in `tests/cli.test.js` (`execFileSync` via the `run()` helper, `assert.match`).

## Out of Scope

- Any subcommand other than `version`.
- Any file other than `bin/cli.js` and `tests/cli.test.js`.
- Cleanup of the pre-existing unused `parseGreetingFormat` helper or its TODO comment.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "node bin/cli.js version", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1 },
    { "cmd": "node --test tests/cli.test.js", "exit_code": 0 }
  ]
}
```
