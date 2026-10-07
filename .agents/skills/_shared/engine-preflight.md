# Shared — Executor Pre-flight

Used by `/devlyn-ideate` and `/devlyn-engines`: one rule for which engine executes implementation work and what happens when it is missing.

## Selection

The executor is the `executor` pin in `.devlyn/engines.json` at the checkout root (set with `/devlyn-engines executor <name>`), else the CLI the user opened. A linked worktree or subdirectory has no pin unless one is set there. Pi and Grok have no executor adapter, so a drain from them needs a claude, codex or omp pin. Keys earlier releases wrote for retired pipeline roles (`pair_judge_priority`, `roles`) stay as written and select nothing: a worker profile never becomes the executor.

Before dispatching to the executor, run:

```sh
python3 "$DEVLYN_SHARED_DIR/role-config.py" --workdir <project> --default-engine <this CLI> --select
```

A pin is a promise. When the pinned engine's CLI is unavailable, the command exits 1 with `BLOCKED:<engine>-unavailable`: stop, preserve the evidence, and show the setup guidance — install and authenticate that CLI, verify `<engine> --version`, rerun. Never substitute another engine. A malformed file, or a name without an executor-eligible adapter, is `BLOCKED:invalid-engine-config`. CLI presence is not authentication, and status never launches a model.

## Engines

An engine is pinnable when `_shared/adapters/<name>.md` exists and does not declare `executor: no` under `## Role eligibility`. Adapters ship with devlyn-cli releases, and a reinstall replaces `_shared`. An adapter's `## Invocation` says how to start it. On native Windows, use native Node/npm and Python (`python3` on PATH), with Git for Windows Bash for the shipped shell wrapper.

## Reporting a blocked engine

The final report names the selected engine, the verdict and the setup steps; it never reports a downgraded success:

```
Engine: codex (pinned executor)
Verdict: BLOCKED:codex-unavailable
Setup: install/configure Codex CLI; run the current Codex auth/login flow; verify `codex --version`; rerun.
```
