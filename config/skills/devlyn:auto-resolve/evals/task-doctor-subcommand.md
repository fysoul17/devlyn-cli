# Task: `devlyn doctor` subcommand

Add a new `doctor` subcommand to `bin/devlyn.js`. When the user runs `npx devlyn-cli doctor` (or `node bin/devlyn.js doctor`), it diagnoses the local devlyn-cli installation and prints a status report.

## Requirements

1. **Node version check** — `process.version >= v18.0.0`. Emit a status line. If below, mark FAIL.
2. **`$HOME/.claude/` check** — exists as directory AND is writable. Missing → FAIL. Exists but not writable (EACCES) → FAIL with a distinct "permission" message.
3. **Installed plugins scan** — read subdirectories of `$HOME/.claude/plugins/cache/` and print a summary line with the count. `--verbose` lists names.
4. **Installed skills scan** — count files matching `$HOME/.claude/skills/**/SKILL.md`. Print count; `--verbose` lists relative paths.
5. **Colored output** — each line prefixed with `[OK]` (green), `[WARN]` (yellow), `[FAIL]` (red) using ANSI escape codes, **only when `process.stdout.isTTY` is true**. Non-TTY → no color codes.
6. **Summary line** — e.g., `doctor: 3 ok, 1 warn, 0 fail`.
7. **Exit code** — `0` if zero fails, `1` if any fail.
8. **`--verbose` flag** — expands details for plugins/skills scans.
9. **Help integration** —
   - `node bin/devlyn.js doctor --help` prints a short help block and exits 0.
   - `node bin/devlyn.js --help` / `node bin/devlyn.js help` lists `doctor` as an available subcommand.

## Constraints

- **Zero new dependencies.** Use only Node.js built-ins (`fs`, `path`, `os`, `process`).
- **No silent error catches.** Per project CLAUDE.md error-handling philosophy, do not wrap operations in `try { … } catch { return fallbackValue }`. All errors visible to the user with actionable messages.
- **HOME guard.** If `process.env.HOME` is undefined or empty, emit a clear FAIL line ("HOME environment variable is not set") and exit 1. Do not attempt to read arbitrary paths.
- **EACCES handling.** If `readdirSync` fails with EACCES, emit a permission-specific message quoting the offending path. Do not silently return an empty list.

## Acceptance verification

Run each of these and they must behave as described:

- `node bin/devlyn.js doctor` — produces the status report, exits 0 on a clean machine.
- `HOME=/nonexistent node bin/devlyn.js doctor` — prints a FAIL line clearly referencing the missing `/nonexistent/.claude`, exits 1.
- `node bin/devlyn.js doctor | cat` — piped output contains no ANSI escape codes (`\x1b[`).
- `node bin/devlyn.js doctor --help` — prints help, exits 0.
- `node bin/devlyn.js --help` — mentions `doctor` in the list of subcommands.
- `git diff -- package.json` — no new entries under `dependencies`.
- `node bin/devlyn.js doctor --verbose` — lists each plugin directory and each skill path.

## Out of Scope

- Auto-repair (don't offer to fix detected problems; just report).
- Checking remote/registry state (npm, GitHub).
- Any feature requiring a new npm dependency.
