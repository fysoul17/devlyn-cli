<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — edit — inside the `case 'version':` block (bin/cli.js:59-62), parse a `--format` flag from `rest`: absent → keep existing `console.log(readPackageVersion())` unchanged (Requirement 3); `--format json` → `console.log(JSON.stringify({ version: readPackageVersion() }))`, which is a single-line valid JSON object reusing the same `readPackageVersion()` value the plain command already reads (Requirements 1–2); any other value → `console.error(...)` + `process.exit(1)`, matching the error style already used by `parseNameFlag` (bin/cli.js:33-42) (Requirement 4).
- `tests/cli.test.js` — edit — add one new `test(...)` (after the existing `version prints package version` test, tests/cli.test.js:22-25) that runs `version --format json` via the existing `run()` helper and asserts the stdout is the literal single-line JSON `{"version":"<x.y.z>"}` (Requirement 5).

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Out-of-scope expansions to refuse**: the `hello` subcommand (bin/cli.js:53-58), the `--help`/`-h` path (bin/cli.js:47-50), the unknown-command `default` case (bin/cli.js:63-66), the unused `parseGreetingFormat` helper (bin/cli.js:29-31), and the two pre-existing `TODO` comments (bin/cli.js:27-28, bin/cli.js:54) — none of these touch the `--format` feature and must remain byte-for-byte identical. No YAML dependency is to be added; unsupported `--format` values (including `yaml`) are simply rejected.
- **`USAGE` constant is implicitly off-limits**: `USAGE` (bin/cli.js:8-19) is written by both the `--help`/`-h` path and the unknown-command path, both of which the Constraints explicitly forbid modifying. Therefore `--format json` will NOT be documented in `USAGE` — adding it would alter the output both forbidden paths print. This is a strict, minimal reading of the constraint, not an oversight.
- **Ambiguous spec resolved strictly**: "print a single-line valid JSON object `{"version":"<x.y.z>"}`" is satisfied verbatim by `JSON.stringify({ version: readPackageVersion() })` — a single-key object has no key-ordering ambiguity, and `JSON.stringify` with no indentation argument is single-line by construction.
- **Missing-value edge case is not special-cased**: `version --format` with no trailing value (or followed by another flag) is not covered by any Requirement or Verification command. `rest[idx + 1]` will be `undefined`, which is `!== 'json'` and therefore falls through to the existing "unsupported value" branch (`console.error` + `exit 1`) with no extra validation code — matching required behavior (exit 1 on non-`json`) without adding speculative robustness or mirroring `parseNameFlag`'s extra `startsWith('-')` guard, which the spec does not require here.
- **Known failure mode**: only the body of `case 'version':` is edited; the surrounding `switch` structure, other `case` blocks, and all whitespace/comments elsewhere in the file are left untouched.

## Acceptance restatement

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "exit_code": 0 },
    { "cmd": "node bin/cli.js version --format json", "exit_code": 0, "stdout_contains": ["{\"version\":\"0.1.0\"}"] },
    { "cmd": "node bin/cli.js version", "exit_code": 0, "stdout_contains": ["0.1.0"], "stdout_not_contains": ["{\"version\""] },
    { "cmd": "node bin/cli.js version --format yaml", "exit_code": 1 }
  ]
}
```
