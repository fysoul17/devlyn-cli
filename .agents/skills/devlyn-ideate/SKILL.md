---
name: devlyn-ideate
description: Loop designer and intent queue. Turns an intent or a document into a validated loop package (a meta-prompt plus self-contained task contracts), appends its tasks to docs/specs/queue.md, reports queue status, and drains the queue serially with evidence-derived acceptance, recovery and delivery. Operations — plan, add, status, drain; a bare intent is planned and, when the request authorizes implementation, continues through add and drain; no arguments shows status. Use when the user wants an idea, goal or document planned into tasks, wants to stack work ("queue this", "큐에 넣어줘"), asks what is queued, or wants unattended execution ("drain the queue", "큐 드레인 시작", "밤새 돌려줘").
---

Ideate owns planning and durable serial execution. Each task runs under the installed methodology, the CLAUDE.md/AGENTS.md instruction block; ideate adds no phase graph, reviewer quota, engine router or restart cycle.

<ideate_args>
$ARGUMENTS
</ideate_args>

<harness_principles>
`_shared/runtime-principles.md`, mirrored in the installed instruction block (read the file only when no block is loaded), binds package content as well as the conversation: a requirement "for future flexibility" violates Subtractive-first, and acceptance that permits a silent fallback violates No-workaround. Flag these while planning, not after execution.
</harness_principles>

<runtime_paths>
Before any operation, establish the bindings below.

Resolve bundled resources from the SKILL.md loaded for this invocation.

Reader-rendered directory hint:
```text
${CLAUDE_SKILL_DIR}
```

Treat the hint as literal path data, never shell code. If the reader
replaced it with an absolute directory, use that directory. Otherwise
use the filesystem path or base directory reported for this loaded
SKILL.md. Resolve virtual URIs through the reader's native filesystem
mapping. If available source locations name different directories,
stop.

Bind DEVLYN_SKILL_DIR to that absolute directory. Do not obtain this
binding from an environment variable, cwd, or another installation.
Verify its SKILL.md before proceeding. Missing or conflicting source
identity is BLOCKED:skill-source-unresolved; include the failed path
when known.

Resolve bundled references against this directory. These bindings are
workflow values: establish them explicitly using each tool or shell's
literal-path rules, and include their absolute values in every fresh
worker's prompt, telling it to set them from those values, never from
its inherited environment. Do not rely on shell state surviving between
calls.

Resolve directory symlinks on DEVLYN_SKILL_DIR before deriving its
sibling _shared. Bind that directory as DEVLYN_SHARED_DIR. References
written as _shared/... use this binding. Verify the directory and each
required resource before use; failure is BLOCKED:shared-dir-unresolved
with the failed path. Never search another installation.

Verify DEVLYN_SKILL_DIR/scripts/queue.py before running it. In omp, use `printf '%s\n' skill://devlyn-ideate`.
</runtime_paths>

## Operations

| Invocation | Behavior |
|---|---|
| `plan <intent or absolute document path>` | Inspect, elicit what is necessary and write a validated loop package. Does not enqueue or execute. |
| `add <intent or absolute package path>` | Plan when necessary, then append the package's tasks atomically in dependency order. Does not execute. |
| `status` | Reconciled pending, active, accepted and failed counts; the next runnable task; delivery and recovery blockers. |
| `drain` | Resume or drain the queue serially under existing execution authorization. |
| Bare intent | Plan; when the request authorizes implementation, continue through add and drain without reconfirmation. |
| No arguments | Status. |

Two controls only: `--autonomous` applies the autonomous policy to plan or add (drain always applies it), and `--local-only` keeps a drain's delivery local (`--no-push` is equivalent). A delivery restriction already established for a loop persists. Engine selection and pins stay project and host settings (`/devlyn-engines`).

A removed flag stops with its instruction and selects no other behavior.

| Flag | Instruction |
|---|---|
| `--quick` | Removed: use `plan <intent>`, adding `--autonomous` to plan without questions. |
| `--from-spec <path>` | Removed: use `plan <absolute path>`; the document stays unchanged as the input contract. |
| `--project` | Removed: every plan is a loop package with as many tasks as the intent needs. |
| `--spec-dir`, `--spec-id`, `--in-place` | Removed: packages live at `docs/specs/<loop-id>/` with generated IDs, and input documents are never rewritten. |
| `--engine` | Removed: drain uses the configured executor; pin it with `/devlyn-engines executor <name>`. |

## Question policy

> Inspect available project facts before asking. Ask only when the unresolved answer changes authorized behavior, scope, data semantics, acceptance or delivery. State the recommended answer and its consequence. Ask the smallest useful question. Stop eliciting when the contract is executable and verifiable; no turn target or mandatory confirmation applies. Existing authorization remains effective.

## Autonomous policy

> Infer only scope-narrowing, reversible, non-user-visible defaults, and record each assumption once. Reversibility alone is insufficient. Material ambiguity stops the affected work as needs-review with a concrete question; independent authorized work may continue. Never weaken acceptance to obtain completion.

## plan

1. Inspect, then elicit, per [elicitation.md](references/elicitation.md). A document argument is the input contract: carry each substantive requirement into a task without weakening it, cite the document in `## Intent`, and never modify it.
2. Write `docs/specs/<loop-id>/meta.md` and each task's `spec.md` and `spec.expected.json` per [package-format.md](references/package-format.md). In the manifest, `base_ref` is the delivery branch and `base_sha` the exact commit the loop builds on; `delivery` is `local-only` when the user restricted delivery, else the project's `git config --local devlyn.completionMode` (absent means `auto`). `## Execution policy` quotes the autonomous policy, which binds every task's executor.
3. Run `python3 "$DEVLYN_SKILL_DIR/scripts/queue.py" check '<absolute meta.md>'` and repair the package until it reports `VALID`.
4. Report the package path, the tasks with their dependencies, and every recorded assumption.

## add

An absolute path to a package's `meta.md` is appended as it is; anything else is planned first. Append with `python3 "$DEVLYN_SKILL_DIR/scripts/queue.py" add '<absolute meta.md>'`, the only writer of new queue rows; never edit `docs/specs/queue.md` by hand. It commits only the package and the queue on the current branch, leaving other staged or unstaged changes as they are, and the loop starts from that commit. A pending legacy raw-intent row is replaced in place by a package whose `## Intent` reproduces the row verbatim, added with `--materialize <line>`.

## status

Run `python3 "$DEVLYN_SKILL_DIR/scripts/queue.py" status --repo .` and report its counts, `next`, `blockers` and pending deliveries with their resume commands.

## drain

Follow [loop.md](references/loop.md). The executor is the configured route, the `.devlyn/engines.json` `executor` pin or else this CLI, checked per `_shared/engine-preflight.md`. Pass it after `--` as an argv that starts one fresh non-interactive session of that engine, able without prompts to edit, run commands and commit in its task worktree and to write the packet's submission file, with the prompt `Execute the devlyn loop task packet {packet}: work only in its owned worktree under the installed instructions; meet its obligations, then write its submission and any review records as "Executor exchange" and "Review records" in <absolute DEVLYN_SKILL_DIR>/references/loop.md specify.`

```sh
python3 "$DEVLYN_SKILL_DIR/scripts/queue.py" drain --repo . [--local-only] -- <executor argv>
```

A drain can run for hours. Do not end the turn until it exits: run it in the foreground with the longest allowed timeout, or in the background and await its completion notice, because a headless host kills background tasks at its final response.

- `WAITING` on legacy rows: plan and materialize each under the autonomous policy, then drain again; a row whose planning stops on material ambiguity stays pending and its question is reported.
- `WAITING` on a delivery or `BLOCKED`: report the reason and resume commands; never edit receipts, refs or queue rows to get past them.
- An interrupted drain is resumed by running `drain` again; accepted work is never replayed.

Report each task's product result, delivery status, PR URL, resume command, assumptions and unresolved questions, plus the drain report paths and its exact `Bring into` command: a local loop's final task branch fast-forwards the branch the loop was added on unless that branch has moved since, and for `auto`/`pr` a pull after delivery fast-forwards it.
