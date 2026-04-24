---
id: "F2-cli-medium-subcommand"
title: "Add `doctor` subcommand to bench-test-repo CLI"
status: planned
complexity: medium
depends-on: []
---

# F2 Add `doctor` subcommand

## Context

`bench-test-repo` users need a one-command way to diagnose their local
environment — node version, Claude Code install, plugins, skills — without
digging through the filesystem. A `doctor` subcommand lands that capability
inside the CLI itself.

## Requirements

- [ ] `node bin/cli.js doctor` produces a status report and exits 0 on a clean machine.
- [ ] Node version check — requires `process.version >= v18.0.0`, emits a status line, marks FAIL if below.
- [ ] `$HOME/.claude/` check — exists as directory AND is writable. Missing → FAIL. Exists but not writable (EACCES) → FAIL with a distinct "permission" message.
- [ ] Installed plugins scan — read subdirectories of `$HOME/.claude/plugins/cache/` and print a summary line with the count; `--verbose` lists names.
- [ ] Installed skills scan — count files matching `$HOME/.claude/skills/**/SKILL.md`; print count; `--verbose` lists relative paths.
- [ ] Colored output with `[OK]` (green), `[WARN]` (yellow), `[FAIL]` (red) via ANSI escape codes **only when `process.stdout.isTTY` is true** — piped output must contain no `\x1b[` sequences.
- [ ] Summary line: `doctor: <N> ok, <M> warn, <K> fail`.
- [ ] Exit code: `0` if zero fails, `1` otherwise.
- [ ] `--verbose` flag expands details for plugins/skills scans.
- [ ] `node bin/cli.js doctor --help` prints a short help block and exits 0.
- [ ] `node bin/cli.js --help` lists `doctor` as an available subcommand.
- [ ] `HOME=/nonexistent node bin/cli.js doctor` prints a FAIL line clearly referencing the missing `/nonexistent/.claude` and exits 1.

## Constraints

- **Zero new npm dependencies.** Use only Node.js built-ins (`fs`, `path`, `os`, `process`).
- **No silent error catches.** Do not wrap operations in `try { … } catch { return fallbackValue }`. All errors visible to the user with actionable messages.
- **HOME guard.** If `process.env.HOME` is undefined or empty, emit a clear FAIL line ("HOME environment variable is not set") and exit 1.
- **EACCES handling.** If `readdirSync` fails with EACCES, emit a permission-specific message quoting the offending path. Do not silently return an empty list.

- **Lifecycle note.** The harness's DOCS phase flips this spec's frontmatter `status` after implementation completes — that is benchmark lifecycle bookkeeping, not a scope violation.

## Out of Scope

- Auto-repair (report only; do not offer to fix detected problems).
- Checking remote/registry state (npm, GitHub).
- Any feature requiring a new npm dependency.

## Verification

- `node bin/cli.js doctor` exits 0 on a machine with `~/.claude` present.
- `HOME=/nonexistent node bin/cli.js doctor` prints a FAIL line referencing `/nonexistent/.claude` and exits 1.
- `node bin/cli.js doctor | cat` contains no `\x1b[` sequences.
- `node bin/cli.js doctor --help` prints help, exits 0.
- `node bin/cli.js --help` mentions `doctor`.
- `git diff -- package.json` is empty.
- `node bin/cli.js doctor --verbose` lists plugins and skills.
