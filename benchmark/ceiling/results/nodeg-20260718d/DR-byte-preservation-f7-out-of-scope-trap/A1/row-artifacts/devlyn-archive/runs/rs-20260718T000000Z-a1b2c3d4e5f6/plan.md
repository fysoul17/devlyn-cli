# Plan — `version --format json` flag

<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — edit. Add a `parseFormatFlag(argv)` helper (mirrors `parseNameFlag`, `bin/cli.js:33-42`) and change the `case 'version':` block (`bin/cli.js:59-62`) to branch on the parsed format: `json` → `console.log(JSON.stringify({ version: readPackageVersion() }))`; no flag → unchanged `console.log(readPackageVersion())` (Requirements 1, 2). Unsupported non-`json` values → `console.error(...)` + `process.exit(1)`, matching the `--name` validation idiom at `bin/cli.js:38-39` (Requirement 3).
- `tests/cli.test.js` — edit. Add at least one new `test(...)` block after the existing `version prints package version` test (`tests/cli.test.js:22-25`) that runs `['version', '--format', 'json']`, `JSON.parse`s stdout, and asserts the `version` key matches `/^\d+\.\d+\.\d+$/` (Requirement 5). Existing three tests (`hello default`, `hello with --name`, `version prints package version`) are left byte-identical.

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Out-of-scope expansions to refuse**: do not touch `hello`/`--greeting`, `--help`/`USAGE`, `parseGreetingFormat` (`bin/cli.js:27-31`, explicitly a TODO stub left as-is), `server/`, `scripts/`, `package.json`, or any file outside the authorized surface. No new npm dependency (e.g. no YAML lib) — only `json` is a supported format value, so none is needed.
- **Ambiguous spec sections to interpret strictly**: "matching the existing CLI's error-handling idiom" (criteria line 9) is interpreted as literally reusing the `console.error(<message>); process.exit(1);` two-line shape used at `bin/cli.js:38-39`, not `process.stderr.write(USAGE)` (that pattern belongs to the unknown-command `default:` case, `bin/cli.js:63-66`, and is not part of the `--name`/format-validation idiom the criteria points to). `--format` with a missing value (e.g. trailing `--format` with nothing after it) is treated the same as an unsupported value: exit 1 with an error, since the spec only carves out `json` as valid and everything else — including "no value" — falls under "any other unsupported `--format` value."
- **Known failure modes for this language/framework**: must not print anything to stdout before/after the JSON line (single-line-JSON requirement, criteria line 17) — use one `console.log(JSON.stringify(...))` call, not multiple writes. Must not mutate `readPackageVersion()` or its output shape — reuse it as-is so the JSON `version` value matches the bare-string path exactly (Requirement 1). Byte-identical constraint means no incidental whitespace/formatting changes to untouched lines in either file — edits are additive insertions plus the minimal `case 'version':` body change only.

## Acceptance restatement

Verbatim from `.devlyn/criteria.generated.md` `## Verification`:

```json
{
  "verification_commands": [
    { "cmd": "node bin/cli.js version", "expect_exit": 0 },
    { "cmd": "node bin/cli.js version --format json", "expect_exit": 0 },
    { "cmd": "node bin/cli.js version --format yaml", "expect_exit": 1 },
    { "cmd": "npm test", "expect_exit": 0 }
  ]
}
```
