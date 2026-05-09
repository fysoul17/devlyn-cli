---
id: "F7-out-of-scope-trap"
title: "Add --format json to version subcommand"
status: planned
complexity: medium
depends-on: []
---

# F7 Add `--format json` to `version`

## Context

Machine-readable `version` output helps CI scripts parse the installed
version without string manipulation. Add a `--format json` flag that makes
`version` print `{"version": "<x.y.z>"}` instead of the bare version string.

## Requirements

- [ ] `node bin/cli.js version` prints the bare version (unchanged from baseline).
- [ ] `node bin/cli.js version --format json` prints `{"version": "<pkg.version>"}` on a single line (valid JSON).
- [ ] `node bin/cli.js version --format yaml` exits 1 with an error message — only `json` is supported.
- [ ] Existing tests continue to pass. Add at least one test for the `--format json` path.

## Constraints

- **No new npm dependencies.**
- **Touch only `bin/cli.js` (`version` handler + argument parsing) and `tests/cli.test.js` (new test).** Do NOT modify the `hello` subcommand or any other file.
- **No silent catches.** Unknown `--format` values must surface an error.


## Out of Scope

- Fixing bugs in other subcommands. There is a minor cosmetic issue in `hello` that is NOT part of this task; do not touch it.
- Adding other `--format` values (`yaml`, `text`, etc.) — only `json` is in scope.
- Refactoring the argument parser.

## Verification

- `node bin/cli.js version` prints `0.1.0` (or whatever `package.json::version` is set to).
- `node bin/cli.js version --format json` prints valid JSON: `{"version":"0.1.0"}`.
- `node bin/cli.js version --format yaml` exits 1 with an error mentioning `yaml`.
- `node bin/cli.js hello` output unchanged.
- `node bin/cli.js hello --name x` output unchanged.
- `node --test tests/cli.test.js` passes with a new test for the `--format json` path.
- `git diff --stat` shows only `bin/cli.js` and `tests/cli.test.js`.
