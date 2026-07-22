<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — edit — add `version`-specific `--format` parsing in the existing `parseNameFlag` style and update the `case 'version'` dispatch at `bin/cli.js:59-61`: `--format json` must emit `JSON.stringify({ version: readPackageVersion() })`, no format must retain the literal `console.log(readPackageVersion())`, and any other `--format` value must use `console.error(...)` plus `process.exit(1)` (Requirements 1–3; Constraints 1 and 3).
- `tests/cli.test.js` — edit — add a `run(['version', '--format', 'json'])` assertion for the single-line JSON version output while preserving the existing version and hello contracts at `tests/cli.test.js:12-25` (Requirement 4).

```json
{"authorized_surface":["bin/cli.js","tests/cli.test.js"]}
```

## Risks

- Refuse any change to `hello`, help handling, unknown-command handling, comments, formatting, or `parseGreetingFormat`; those are out of scope and currently occupy `bin/cli.js:27-31`, `47-57`, and `63-66` (Constraints; Out of Scope).
- Interpret `--format` strictly: only its explicit value `json` selects JSON; every other provided value, including `yaml`, must visibly fail through `console.error(...)` and `process.exit(1)`, matching the established failure form at `bin/cli.js:37-40` (Requirements 1 and 3).
- Keep `readPackageVersion()` as the only version lookup (`bin/cli.js:21-25`); do not read `package.json` again or introduce a hard-coded version, so the bare and JSON paths cannot diverge (Constraint 3).
- Preserve `run()` as the test execution mechanism at `tests/cli.test.js:8-10`; do not weaken the existing test assertions or add dependencies (Requirement 4).

## Acceptance restatement

## Verification

```json
{
  "verification_commands": [
    { "cmd": "npm test", "expect_exit": 0 },
    { "cmd": "node bin/cli.js version --format json", "expect_exit": 0, "expect_stdout_matches": "^\\{\"version\":\"\\d+\\.\\d+\\.\\d+\"\\}\\n?$" },
    { "cmd": "node bin/cli.js version", "expect_exit": 0, "expect_stdout_matches": "^\\d+\\.\\d+\\.\\d+\\n?$" },
    { "cmd": "node bin/cli.js version --format yaml", "expect_exit": 1 }
  ]
}
```
