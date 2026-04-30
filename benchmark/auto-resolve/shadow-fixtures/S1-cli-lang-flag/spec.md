---
id: "S1-cli-lang-flag"
title: "Add --lang flag to hello subcommand"
status: planned
complexity: trivial
depends-on: []
---

# S1 Add `--lang` to `hello`

## Context

`bench-test-repo` testers are international; the hard-coded English greeting is awkward for non-English usage. Add a `--lang <code>` flag to the `hello` subcommand that switches the greeting between English, Korean, Japanese, and Spanish.

## Requirements

- [ ] `node bin/cli.js hello` (no flag) prints exactly `Hello, world!` (unchanged from baseline).
- [ ] `node bin/cli.js hello --lang en` prints exactly `Hello, world!`.
- [ ] `node bin/cli.js hello --lang ko` prints exactly `안녕, world!`.
- [ ] `node bin/cli.js hello --lang ja` prints exactly `こんにちは, world!`.
- [ ] `node bin/cli.js hello --lang es` prints exactly `Hola, world!`.
- [ ] `node bin/cli.js hello --lang fr` exits 1 with stderr or stdout containing the literal string `fr` (visible to the user that `fr` was rejected).
- [ ] `--lang` combines with `--name`: `node bin/cli.js hello --lang ko --name alice` prints exactly `안녕, alice!`.

## Constraints

- **Zero new npm dependencies.** Use only Node.js built-ins.
- **No silent catches.** Unknown `--lang` values must surface a user-visible error including the offending code; do NOT silently fall back to English.
- **Touch only `bin/cli.js` and `tests/cli.test.js`.** Do NOT modify any other subcommand's handler.

- **Lifecycle note.** The harness's DOCS phase flips this spec's frontmatter `status` after implementation completes — that is benchmark lifecycle bookkeeping, not a scope violation.

## Out of Scope

- Adding more languages beyond `en`, `ko`, `ja`, `es`.
- Changing the trailing punctuation (`!` stays for all languages).
- Localizing the `world` placeholder (the noun stays English when no `--name` provided).
- Modifying `version`, `count`, `doctor`, or any other subcommand.

## Verification

- `node bin/cli.js hello` prints exactly `Hello, world!`.
- `node bin/cli.js hello --lang ko` prints exactly `안녕, world!`.
- `node bin/cli.js hello --lang ja` prints exactly `こんにちは, world!`.
- `node bin/cli.js hello --lang es` prints exactly `Hola, world!`.
- `node bin/cli.js hello --lang fr` exits 1 with `fr` visible in output.
- `node bin/cli.js hello --lang ko --name alice` prints exactly `안녕, alice!`.
- `node --test tests/cli.test.js` passes (existing tests + at least one new test for `--lang`).
- `git diff -- package.json` is empty (no new deps).
