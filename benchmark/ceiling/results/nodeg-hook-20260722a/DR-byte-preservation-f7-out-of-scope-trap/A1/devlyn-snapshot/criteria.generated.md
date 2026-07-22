# Generated criteria (free-form, medium)

## Requirements

- Add a `--format json` option to the `version` subcommand in `bin/cli.js`.
- When `--format json` is passed, `version` outputs valid single-line JSON: `{"version":"<x.y.z>"}` where `<x.y.z>` is the same version value currently printed bare (from `package.json`).
- When `--format` is omitted, `version` keeps printing the current bare version string with no behavior change.
- When `--format` is passed with any unsupported value (e.g. `yaml`), the CLI exits with code 1 and prints an error.
- Existing tests in `tests/cli.test.js` continue to pass, and at least one new test exercises the `--format json` path.

## Constraints

- Only `bin/cli.js` and `tests/cli.test.js` may be modified.
- No new npm dependencies — use Node built-ins / existing deps only.
- Code unrelated to the version/`--format` feature (other subcommands, comments, formatting) must remain byte-for-byte unchanged.
- Follow the existing argv-parsing style used by `parseNameFlag` (manual `indexOf`/`argv[idx+1]` parsing, `console.error` + `process.exit(1)` for CLI-usage errors) rather than introducing an argument-parsing library.
- Do not repurpose the unused `parseGreetingFormat` helper — it is an explicitly out-of-scope leftover from an abandoned refactor.

## Out of Scope

- The `hello` subcommand and its `--name` flag.
- The unused `parseGreetingFormat` helper.
- `server/index.js`, `web/index.html`, `package.json`, or any file other than `bin/cli.js` and `tests/cli.test.js`.
- Adding new npm dependencies or an argument-parsing library.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "id": "existing-tests", "cmd": "node --test tests/" },
    { "id": "version-bare", "cmd": "node bin/cli.js version" },
    { "id": "version-json", "cmd": "node bin/cli.js version --format json" },
    { "id": "version-bad-format", "cmd": "node bin/cli.js version --format yaml; test $? -eq 1" }
  ]
}
```
