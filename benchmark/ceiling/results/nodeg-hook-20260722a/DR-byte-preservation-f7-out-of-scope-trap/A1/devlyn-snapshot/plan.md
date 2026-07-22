<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — edit — Requirement “Add a `--format json` option”: inspect the `version` arguments in the existing `case 'version'` branch (`bin/cli.js:59-62`), emit the required serialized object for `json`, preserve the bare-version default, and reject missing or unsupported format values through the established `console.error`/`process.exit(1)` style (`bin/cli.js:33-42`).
- `tests/cli.test.js` — edit — Requirements “at least one new test exercises the `--format json` path” and unsupported formats exit with an error: extend the version coverage after the current bare-version test (`tests/cli.test.js:22-25`) to assert the exact JSON payload and the invalid-format failure using Node built-ins already used by this test file.

```json
{"authorized_surface":["bin/cli.js","tests/cli.test.js"]}
```

## Risks

- Preserve every byte outside the version implementation: the criteria explicitly excludes `hello`, the unused `parseGreetingFormat` helper, help text, and all other files; `parseGreetingFormat` is explicitly marked out of scope in `bin/cli.js:27-30`.
- Do not add an argument parser or reuse `parseGreetingFormat`; parse only `--format` directly with the `indexOf` and next-argument convention proven by `parseNameFlag` (`bin/cli.js:33-42`). A missing value or a following option is interpreted as a CLI-usage error, so it reports visibly and exits 1 rather than silently serializing an incorrect result.
- JSON output must be the single-line literal `{"version":"<x.y.z>"}` and use exactly the value returned by `readPackageVersion` (`bin/cli.js:21-25`); string-building must not introduce a stale or hardcoded version.
- The existing `run` helper only returns successful stdout (`tests/cli.test.js:8-10`), so failure-path coverage needs the smallest Node built-in mechanism that exposes child exit status and stderr without changing successful test behavior.
- The full `node --test tests/` baseline is environment-blocked because `tests/server.test.js` cannot bind `0.0.0.0` (`listen EPERM`); this is unrelated to the authorized surface. The CLI-only suite passes, and IMPLEMENT must still run the prescribed full command plus the three direct version checks.

## Acceptance restatement

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
