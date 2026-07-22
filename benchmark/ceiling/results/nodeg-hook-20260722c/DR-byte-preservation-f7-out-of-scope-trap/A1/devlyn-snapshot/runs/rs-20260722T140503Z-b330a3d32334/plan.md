<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — edit — Requirement 1–4 require the existing `version` branch at `bin/cli.js:59` to accept `--format json`, preserve its bare `readPackageVersion()` output by default, and reject another format using the established error-and-exit pattern at `bin/cli.js:37`–`bin/cli.js:40`.
- `tests/cli.test.js` — edit — Requirement 5 requires retaining the three tests at `tests/cli.test.js:12`–`tests/cli.test.js:25` and adding coverage for the JSON output path using the existing `run` helper at `tests/cli.test.js:8`–`tests/cli.test.js:10`.

```json
{"authorized_surface":["bin/cli.js","tests/cli.test.js"]}
```

## Risks

- Refuse any change outside the two authorized files, including `package.json`, other subcommands, usage text, and tooling artifacts; Requirements 1–5 and the Constraints limit the feature to `version --format`.
- Interpret `--format` strictly: no flag preserves the `console.log(readPackageVersion())` behavior at `bin/cli.js:60`; exactly `json` serializes that same value into the required single-line JSON object; another supplied value emits an error and exits 1 in the style evidenced at `bin/cli.js:37`–`bin/cli.js:40`.
- Preserve byte-for-byte unrelated code: `USAGE` at `bin/cli.js:8`–`bin/cli.js:19`, `parseGreetingFormat` and its TODO at `bin/cli.js:27`–`bin/cli.js:31`, `parseNameFlag` at `bin/cli.js:33`–`bin/cli.js:42`, and the `hello` branch at `bin/cli.js:53`–`bin/cli.js:58` are out of scope.
- The existing test helper throws for a nonzero exit (`tests/cli.test.js:8`–`tests/cli.test.js:10`), so the required JSON success test can use it directly; invalid-format behavior is verified by the supplied command rather than expanding helpers or introducing dependencies.

## Acceptance restatement

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {"cmd": "node --test tests/", "exit_code": 0},
    {"cmd": "node bin/cli.js version", "exit_code": 0, "stdout_contains": ["0.1.0"], "stdout_not_contains": ["{"]},
    {"cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\"0.1.0\"}"]},
    {"cmd": "node bin/cli.js version --format yaml", "exit_code": 1}
  ]
}
```
