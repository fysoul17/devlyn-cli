---
id: "F6-dep-audit-native-module"
title: "Implement `checksum <file>` using Node crypto (no new deps)"
status: planned
complexity: medium
depends-on: []
---

# F6 `checksum` subcommand

## Context

`bench-test-repo`'s CLI needs a `checksum` subcommand that prints the
SHA-256 hex digest of a file's contents. Node's built-in `crypto` module
already provides everything needed; no external dependency is warranted.

## Requirements

- [ ] `node bin/cli.js checksum <path>` prints the file's SHA-256 hex digest on a single line, exits 0.
- [ ] Missing argument → prints a clear error, exits 1.
- [ ] File not found → prints `Error: file not found: <path>` to stderr, exits 2.
- [ ] Directory passed → prints `Error: not a file: <path>` to stderr, exits 2.
- [ ] Behavior matches `sha256sum` / `shasum -a 256` for the given file.
- [ ] Add at least one test under `tests/` that creates a fixture file and asserts the expected digest.
- [ ] Existing subcommands (`hello`, `version`) unchanged.

## Constraints

- **Zero new npm dependencies.** Use only Node built-ins (`crypto`, `fs`, `path`, `stream`). Any addition to `dependencies` or `devDependencies` is a disqualifier.
- **Stream-friendly.** Large files should not be read fully into memory. Use a hash stream (`crypto.createHash('sha256')` + pipe from `fs.createReadStream`).
- **No silent catches.** File I/O errors must surface with an informative message and the appropriate exit code.

- **Lifecycle note.** The harness's DOCS phase flips this spec's frontmatter `status` after implementation completes — that is benchmark lifecycle bookkeeping, not a scope violation.

## Out of Scope

- MD5 / SHA-1 / other algorithms.
- Verification mode (comparing against a provided digest).
- Recursive directory hashing.
- Touching `server/` or `web/`.

## Verification

- `printf 'hello\n' > /tmp/bench-f6-sample && node bin/cli.js checksum /tmp/bench-f6-sample` prints `5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03`.
- `node bin/cli.js checksum` exits 1 with stderr message.
- `node bin/cli.js checksum /nonexistent-path-9876` exits 2.
- `node bin/cli.js checksum /tmp` exits 2 (directory).
- `node --test tests/checksum.test.js` passes.
- `git diff HEAD -- package.json` is empty.
