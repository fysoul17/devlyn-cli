---
id: "F1-cli-trivial-flag"
title: "Add --loud flag to hello subcommand"
status: planned
complexity: trivial
depends-on: []
---

# F1 Add `--loud` flag to `hello`

## Context

The `hello` subcommand in `bin/cli.js` currently prints `Hello, <name>!`. A
`--loud` flag gives users an emphatic variant without breaking the default.
This is a low-risk edit used to calibrate trivial-tier fixture difficulty.

## Requirements

- [ ] `node bin/cli.js hello --loud` prints `HELLO, WORLD!!` (everything uppercased, two trailing exclamation marks).
- [ ] `node bin/cli.js hello --loud --name alice` prints `HELLO, ALICE!!`.
- [ ] `node bin/cli.js hello` (no flag) still prints `Hello, world!` (unchanged).
- [ ] `node bin/cli.js hello --name bob` still prints `Hello, bob!` (unchanged).
- [ ] Existing tests continue to pass. Add at least one test covering the `--loud` path.

## Constraints

- **No new npm dependencies.** Built-ins only.
- **No silent catches.** If an unknown flag is passed, exit 1 with an informative message (same pattern as the existing `--name` handler).
- **Surgical diff.** Only touch `bin/cli.js` and `tests/cli.test.js`. Do not reformat unrelated code.

- **Lifecycle note.** The harness's DOCS phase flips this spec's frontmatter `status` after implementation completes — that is benchmark lifecycle bookkeeping, not a scope violation.

## Out of Scope

- Adding unrelated flags (`--quiet`, `--locale`, etc.).
- Refactoring the existing argument parser.
- Touching `server/`, `web/`, or `tests/server.test.js`.

## Verification

- `node bin/cli.js hello` prints `Hello, world!` (exit 0).
- `node bin/cli.js hello --loud` prints `HELLO, WORLD!!` (exit 0).
- `node bin/cli.js hello --loud --name alice` prints `HELLO, ALICE!!` (exit 0).
- `node --test tests/` passes all tests including the new `--loud` case.
- `git diff --stat` shows only `bin/cli.js` and `tests/cli.test.js` touched.
