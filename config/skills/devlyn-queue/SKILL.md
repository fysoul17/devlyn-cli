---
name: devlyn-queue
description: Manage and drain the intent queue (docs/specs/queue.md) — the backlog the loop-engineering contract runs on. Use when the user wants to stack work for later ("큐에 넣어줘", "queue this"), see what is queued, or start an unattended serial drain ("큐 드레인 시작", "밤새 돌려줘", "drain the queue") that takes each item through spec → /devlyn-resolve → verified done.
---

Utility front-end for the intent-queue contract in the project instructions ("Intent queue" in CLAUDE.md / AGENTS.md — whichever this CLI loads). It adds no semantics of its own: the queue file is the API, and the drain loop follows the documented contract exactly — a runner (this skill, a long session, or a future devlyn-os daemon) is a replaceable driver over the same file.

<args>
$ARGUMENTS
</args>

Before `add` or `drain`, establish the bindings below.

Resolve bundled resources from the SKILL.md loaded for this invocation.

Reader-rendered directory hint:
```text
${CLAUDE_SKILL_DIR}
```

Treat the hint as literal path data, never shell code. If the reader
replaced it with an absolute directory, use that directory. Otherwise
use the filesystem path or base directory reported for this loaded
SKILL.md. Resolve virtual URIs through the reader's native filesystem
mapping. If available source locations disagree, stop.

Bind DEVLYN_SKILL_DIR to that absolute directory. Do not obtain this
binding from an environment variable, cwd, or another installation.
Verify its SKILL.md before proceeding. Missing or conflicting source
identity is BLOCKED:skill-source-unresolved; include the failed path
when known.

Resolve bundled references against this directory. These bindings are
workflow values: establish them explicitly using each tool or shell's
literal-path rules, and include their absolute values in every fresh
worker's prompt. Do not rely on shell state surviving between calls.

Resolve directory symlinks on DEVLYN_SKILL_DIR before deriving its
sibling _shared. Bind that directory as DEVLYN_SHARED_DIR. References
written as _shared/... use this binding. Verify the directory and each
required resource before use; failure is BLOCKED:shared-dir-unresolved
with the failed path. Never search another installation.

For `add`, verify DEVLYN_SKILL_DIR/scripts/append.py before invoking it. For `drain`, before processing the first item, read and obey ../devlyn-resolve/references/outer-loop.md (its scoped-commit order is binding) and read ../devlyn-resolve/references/task-completion.md, both relative to this bound skill directory. Load the sibling devlyn-resolve/SKILL.md by its absolute path and preserve this bundle's DEVLYN_SHARED_DIR when handing off; do not rediscover resolve by its bare command name. In omp, use `printf '%s\n' skill://devlyn-queue`.

Queue state is base's `docs/specs/queue.md` plus owned receipts: for each `$(git rev-parse --git-common-dir)/devlyn-completion/*/receipt.json`, read `git show <ref>:docs/specs/queue.md` from its `recovery_ref` if that ref exists (it is never deleted), else its `branch` if it still exists; an item unmarked on base but `[x]`/`[F]` there counts as that mark. Two different terminal marks for one item stop for inspection. Status and drain selection both use this view.

## No args — status

Read the queue state above (absent `docs/specs/queue.md` → report "queue empty — nothing staged" and how to add). Print pending `[ ]`, done `[x]`, and blocked `[F]` counts, the next item up, and one usage line per subcommand.

## Subcommands

- `add <intent text>` — use the Write tool to place the exact full intent in a new file `.devlyn/queue-intent-<unique>.txt` (a name no other add uses, made of letters, digits, `.`, `_` and `-`, e.g. `queue-intent-20261001-1230-k3x9.txt`); do not create it with shell syntax. If the conversation already produced a spec, the file must start with `(spec: docs/specs/<id>/spec.md)`. Then, from the project root, run exactly once `python3 "$DEVLYN_SKILL_DIR/scripts/append.py" .devlyn/queue-intent-<unique>.txt`. The helper consumes that file, appends one `- [ ] <intent>` line at the physical end of `docs/specs/queue.md` under a lock (creating it with its header if missing), and is the sole queue writer. Never edit `docs/specs/queue.md` directly for `add` and never use a direct-edit fallback; a nonzero helper exit is shown to the user and stops the `add`.
- `drain` — serial drain per the project-instructions contract. For each pending item, in order:
  1. Allocate the owner's absent task branch with `--worktree <absent path>` per `../devlyn-resolve/references/task-completion.md`, and work in that worktree; then spec it if unspecced (the queue entry is the user's go-ahead). Unattended assumptions may only take scope-narrowing, reversible, non-user-visible defaults; material ambiguity (user-visible behavior, data/state semantics, new files/scripts/flags, implementation surface) → mark `[F] needs-review: <question>`, commit that queue transition, and continue.
  2. Bring only the current queue-item delta and linked spec bundle from the queue view into the task worktree, which starts from the fetched remote base with no other local commits, commit that scoped owner baseline, then run `/devlyn-resolve --spec <path>` hands-free.
     After every resolve invocation, run `python3 "$DEVLYN_SHARED_DIR/terminal-claim-check.py" .`; exit 79 marks `[F] FAILED-INCOMPLETE` from the predicate, never from the session self-report.
  3. Outer loop on the terminal verdict: PASS → mark `[x]`. Findings-backed verdicts (NEEDS_WORK, BLOCKED:repair-budget-exhausted) → amend the spec, commit that scoped amendment, then re-run — at most 3 outer iterations. Infrastructure / invalid-input / engine-availability / implement-empty BLOCKED verdicts are not spec-amendable → mark `[F] <verdict>` immediately.
  4. Commit each terminal `[x]` / `[F]` queue transition before advancing. For successfully archived normal runs, invoke owner completion once after that declared queue-file-only commit; bind it separately from the verified source. Honor local-only/no-push. Failed products never publish. Retain PR/pending workspaces and use a separate owned branch from base for the next item; unavailable safe placement stops the drain with remaining items pending. A product-blocked item otherwise never halts the queue.
  5. When the queue is drained (or the session must stop), emit the drain report: per-item product verdict and separate delivery status/URL/resume, every logged assumption, and the commit range produced.

Strictly SERIAL — one `/devlyn-resolve` run at a time, never parallel. Never invent queue items, never reorder them, and never delete an item — only mark `[x]` / `[F]`.
