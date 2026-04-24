---
id: "F5-fix-loop-red-green"
title: "Implement `count` subcommand to pass existing failing tests"
status: planned
complexity: medium
depends-on: []
---

# F5 Implement `count` subcommand

## Context

`tests/count.test.js` has been committed to the repo with tests that
currently fail because the `count` subcommand doesn't exist in `bin/cli.js`.
Implement it so every test passes.

## Requirements

- [ ] `node bin/cli.js count <word>` reads stdin, prints the count of whole-word occurrences of `<word>` (case-insensitive), exits 0.
- [ ] Whole-word matching: `cat` does NOT match inside `category` or `scattered`.
- [ ] Case-insensitive: `Cat`, `CAT`, and `cat` all match when the argument is `cat`.
- [ ] Empty stdin → prints `0`, exits 0.
- [ ] Missing `<word>` argument → prints a clear error, exits 1.
- [ ] Word with leading/trailing whitespace in the argument is trimmed before matching.
- [ ] All tests in `tests/count.test.js` pass without modification.
- [ ] The existing `hello` and `version` subcommands continue to work.

## Constraints

- **No new npm dependencies.** Built-ins only.
- **Do not modify `tests/count.test.js`.** If a test looks wrong, that's a signal to revisit the implementation, not the test.
- **No silent catches.** Errors reading stdin must surface with a clear message (not suppressed).

- **Lifecycle note.** The harness's DOCS phase flips this spec's frontmatter `status` after implementation completes — that is benchmark lifecycle bookkeeping, not a scope violation.

## Out of Scope

- Handling binary stdin.
- Regex-pattern matching (the argument is a literal word).
- Counting in a file (only stdin).
- Touching `server/` or `web/`.

## Verification

- `node --test tests/count.test.js` — all tests pass.
- `echo 'cat hat CAT category' | node bin/cli.js count cat` prints `2`.
- `echo '' | node bin/cli.js count cat` prints `0`.
- `node bin/cli.js count` (no arg) exits 1 with an error line.
- `node bin/cli.js hello` still prints `Hello, world!`.
