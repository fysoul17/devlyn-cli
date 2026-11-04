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

Fresh sessions of Claude, Codex and omp on macOS and Linux. Other engines, Windows, and these
arguments stop the launch with a reason, because the plan could not describe the session:

| Engine | Refused | Why |
|---|---|---|
| Claude | `-c`, `--continue`, `-r`, `--resume`, `--fork-session`, `--from-pr` | continues a session |
| Claude | `--settings`, `--setting-sources` | changes settings the merge reads |
| Codex | `resume`, `fork`, `exec resume`, `exec fork` | continues a session |
| Codex | `-p`, `--profile`; `-c` on `developer_instructions`, `plugins`, `skills`, `marketplaces` | changes settings the plan writes |
| omp | `-c`, `--continue`, `-r`, `--resume`, `--restore`, `--from-claude`, `--from-codex`; `autoResume` outside `-p` | continues a session |
| omp | `--config`, `--profile` | changes settings the merge reads |

Claude's and omp's `--append-system-prompt` and Claude's `--append-system-prompt-file` are merged
into the plan's single appended prompt; more than one is refused.

Tests: `python3 scripts/test-harness-run.py` packs this checkout and runs it against fake engines.
