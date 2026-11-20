# Shared — Executor Pre-flight

## Selection

Each role has one answer where a session works: the pin in `.devlyn/engines.json` of its working directory, normally the checkout root (set with `/devlyn-engines executor <name>`), else the user's pin for every project in `~/.devlyn/engine-defaults.json` (set by saying it for every project), else for the executor the CLI the user opened and for reviewers nobody named. An empty list is no pin. A linked worktree or subdirectory has no pin of its own unless one is set there, so there the user's applies. A drained task is the exception: its drain records the checkout it runs in beside the task's packet at every start, and the run reads that checkout's pins with `--packet <packet>` in place of `--workdir`, stopping without a submission when that is refused (`BLOCKED:no-drain-checkout`). Only Claude and Codex can execute, so a drain from any other CLI needs a claude or codex pin. Keys earlier releases wrote for retired pipeline roles (`pair_judge_priority`, `roles`) stay as written and select nothing: a worker profile never becomes the executor.

The user's executor pin may name a model and an effort (`engine/model`, `engine/model/effort`); a checkout's names an engine alone. A pin that names a model is always a fresh run of that engine, started as its adapter's `## Invocation` says with the model and effort: no session judges whether its own model is the pinned one. Say in the prompt of every run you start to implement that it was started to implement. A run started that way is the executor: it implements and never hands the implementation on. That run works unattended, with the permissions its adapter's line gives it, as a run of another pinned engine always has.

Before dispatching to the executor, run:

```sh
python3 "$DEVLYN_SHARED_DIR/role-config.py" --workdir <project> --default-engine <this CLI> --select
```

The command prints `executor` (engine, model, effort, and `source`: `engines.json` for the checkout's pin, `user`, or `default`) and `review_with`, the reviewers to start here. A pin is a promise, from either file. When the pinned engine's CLI is unavailable, the command exits 1 with `BLOCKED:<engine>-unavailable`: stop, preserve the evidence, and show the setup guidance — install and authenticate that CLI, verify `<engine> --version`, rerun. Never substitute another engine. A malformed file, or a name this release cannot start as executor, is `BLOCKED:invalid-engine-config`. CLI presence is not authentication, and status never launches a model.

## Engines

An engine is pinnable when `_shared/adapters/<name>.adapter.md` exists and does not declare `executor: no`. Adapters ship with devlyn-cli releases, and a reinstall replaces `_shared`. An adapter's `## Invocation` says how to start it. On native Windows, use native Node/npm and Python (`python3` on PATH), with Git for Windows Bash for the shipped shell wrapper.

## Reviewers

Pinned reviewers are the reviewers the user requires (principle 4). The status command prints them under `review_with`, each with its start command, taken from its adapter's `## Review` section: a fresh read-only run that is given the requirement and the change, never the working conversation. (`reviewers` in that status is the checkout's own list alone, kept for apps released before the user's file.) One whose stored model or effort its review cannot take has no start there and is `unsupported`: it is not started on another model. Pin them with `/devlyn-engines reviewers <name>...`; a name is an engine with a review section, optionally `engine/model` or `engine/model/effort` where that section takes them.

A reviewer that cannot start (not installed, not signed in, out of usage, a start error) is named with its reason in the report, and the others still review. When none can start, principle 4's rule for no named reviewer applies. Never sign in, switch accounts or change settings to make a reviewer start. With no reviewers pinned, nothing here applies and no engine is chosen for the user.

## Reporting a blocked engine

The final report names the selected engine, the verdict and the setup steps; it never reports a downgraded success:

```
Engine: codex (pinned executor)
Verdict: BLOCKED:codex-unavailable
Setup: install/configure Codex CLI; run the current Codex auth/login flow; verify `codex --version`; rerun.
```
