# Generated criteria — add `--format json` to `version` subcommand

Source: `.devlyn/goal.raw.txt` (free-form goal, complexity: medium).

Context anchors read at classification time:
- `bin/cli.js` — `version` case currently does `console.log(readPackageVersion())`; flag parsing precedent is `parseNameFlag(rest)` for `hello --name`, which validates the flag value and calls `process.exit(1)` with a `console.error` message on invalid input.
- `tests/cli.test.js` — uses `node:test` + `execFileSync('node', [CLI, ...args], { encoding: 'utf8' })`; existing `version prints package version` test asserts `/\d+\.\d+\.\d+/` on stdout.

## Requirements

- [ ] `bench-cli version --format json` prints a single line of valid JSON `{"version":"<x.y.z>"}` to stdout, where `<x.y.z>` is the exact version string from `package.json`.
- [ ] `bench-cli version` with no `--format` flag keeps printing the current bare version string (unchanged behavior).
- [ ] `bench-cli version --format yaml` (or any other unsupported `--format` value) exits with code 1 and prints an error.
- [ ] All existing tests in `tests/cli.test.js` continue to pass.
- [ ] At least one new test in `tests/cli.test.js` covers the `--format json` path.

## Constraints

- Only `bin/cli.js` and `tests/cli.test.js` may be modified.
- No new npm dependencies.
- Do not modify other subcommands (`hello`, `--help`/`-h`, unknown-command handling).
- Code unrelated to the `version` feature — including existing comments, the two `TODO` comments, the unused `parseGreetingFormat` helper, and formatting — must remain byte-for-byte as-is.

## Out of Scope

- Refactoring or cleanup of `hello`, `parseNameFlag`, `parseGreetingFormat`, or `USAGE`.
- Any change to `readPackageVersion`'s error handling beyond what `--format` requires.
- Anything not in the listed files.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "node -e \"const {execFileSync}=require('child_process'); const pkg=require('./package.json'); const out=execFileSync('node',['bin/cli.js','version','--format','json'],{encoding:'utf8'}); const expected=JSON.stringify({version:pkg.version})+'\\n'; if(out!==expected){console.error('mismatch: '+JSON.stringify(out)); process.exit(1);} console.log('FORMAT_JSON_OK');\"",
      "exit_code": 0,
      "stdout_contains": ["FORMAT_JSON_OK"],
      "stdout_not_contains": []
    },
    {
      "cmd": "node -e \"const {execFileSync}=require('child_process'); const out=execFileSync('node',['bin/cli.js','version'],{encoding:'utf8'}); if(!/^\\d+\\.\\d+\\.\\d+\\n$/.test(out)){console.error('mismatch: '+JSON.stringify(out)); process.exit(1);} console.log('BARE_VERSION_OK');\"",
      "exit_code": 0,
      "stdout_contains": ["BARE_VERSION_OK"],
      "stdout_not_contains": []
    },
    {
      "cmd": "node -e \"const {execFileSync}=require('child_process'); try { execFileSync('node',['bin/cli.js','version','--format','yaml'],{encoding:'utf8'}); console.error('expected nonzero exit'); process.exit(1); } catch(e){ if(e.status!==1){console.error('wrong exit code: '+e.status); process.exit(1);} console.log('FORMAT_YAML_REJECTED'); }\"",
      "exit_code": 0,
      "stdout_contains": ["FORMAT_YAML_REJECTED"],
      "stdout_not_contains": []
    },
    {
      "cmd": "npm test",
      "exit_code": 0,
      "stdout_contains": [],
      "stdout_not_contains": ["not ok"]
    }
  ]
}
```
