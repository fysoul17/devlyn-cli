# `devlyn run`

```text
devlyn run <claude|codex|omp> [engine arguments...]
```

Starts an engine from a terminal with the activation plan the Devlyn app applies, so a
terminal session gets the selected release's principles and skills
([harness-activation.md](harness-activation.md)). Everything after the engine name belongs to
the engine. Preparation either completes or no engine starts: there is no fallback to a raw launch.
stdout, stdin and the exit code or signal are the engine's; one status line goes to stderr.

## Release

1. An unfinished queue's binding in this repository (`<git-common-dir>/devlyn-loops/harness.json`).
2. The app's default release (`~/.devlyn/harness/state.json`, read only).
3. Only when neither is recorded, this package, captured once into `~/.devlyn/cli/releases`.

A recorded release that is unreadable, missing or changed stops the launch; it never yields to
another release. The machine's or the repository's recorded choice applies: `none` starts the
engine without activation and says so.

## Scope

Fresh sessions of Claude, Codex and omp on macOS and Linux. Other engines and Windows stop the
launch with a reason.

Only arguments known not to change the session's freshness, its directory, or the settings the plan
merges pass through (`OPTIONS` in `bin/harness-context.js`: model, permission, output and similar
options). Anything else stops the launch with `run-argument-unsupported`, so an attached short
option, an alias or a future flag cannot slip past. Directory-changing options are refused: `cd` first.

A prompt with a space passes as it is. A one-word positional could be the engine's own command
(`claude attach`, `codex resume`), so a one-word prompt, or any text starting with a dash, goes after
`--`: `devlyn run claude -p -- hello`. Codex's `exec` (or `e`) and `debug prompt-input` are the only
commands that pass. Continuing a session stops with `run-continuation-unsupported`: Codex `resume` and
`fork`, and omp's `autoResume` outside `-p`.

The plan's own settings are merged rather than overwritten: Claude's and omp's
`--append-system-prompt`, Claude's `--append-system-prompt-file` (one of them, not several) and
`--plugin-dir`. omp reads a file named on its flag, and without the flag its `.omp/APPEND_SYSTEM.md` or
`~/.omp/agent/APPEND_SYSTEM.md`, which the plan's explicit prompt would otherwise replace; both are
carried into the merged text. omp's other config folders are not searched for that file.

When the recorded choice is `none`, nothing is planned and every argument passes through unchanged.

Tests: `python3 scripts/test-harness-run.py` packs this checkout and runs it against fake engines.
