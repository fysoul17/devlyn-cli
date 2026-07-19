---
name: devlyn:queue
description: Manage and drain the intent queue (docs/specs/queue.md) — the backlog the loop-engineering contract runs on. Use when the user wants to stack work for later ("큐에 넣어줘", "queue this"), see what is queued, or start an unattended serial drain ("큐 드레인 시작", "밤새 돌려줘", "drain the queue") that takes each item through spec → /devlyn:resolve → verified done.
---

Utility front-end for the intent-queue contract in the project instructions ("Intent queue" in CLAUDE.md / AGENTS.md — whichever this CLI loads). It adds no semantics of its own: the queue file is the API, and the drain loop follows the documented contract exactly — a runner (this skill, a long session, or a future devlyn-os daemon) is a replaceable driver over the same file.

<args>
$ARGUMENTS
</args>

## No args — status

Read `docs/specs/queue.md` (absent → report "queue empty — nothing staged" and how to add). Print pending `[ ]`, done `[x]`, and blocked `[F]` counts, the next item up, and one usage line per subcommand.

## Subcommands

- `add <intent text>` — append `- [ ] <intent>` to `docs/specs/queue.md` (create the file with its header if missing). If the intent came out of a conversation that already produced a spec, link it: `- [ ] (spec: docs/specs/<id>/spec.md) <intent>`.
- `drain` — serial drain per the project-instructions contract. For each pending item, in order:
  1. Spec it if unspecced (the queue entry is the user's go-ahead). Unattended assumptions may only take scope-narrowing, reversible, non-user-visible defaults; material ambiguity (user-visible behavior, data/state semantics, new files/scripts/flags, implementation surface) → mark `[F] needs-review: <question>` and continue to the next item.
  2. Run `/devlyn:resolve --spec <path>` hands-free.
     After every resolve invocation, run `python3 benchmark/ceiling/scripts/terminal-claim-check.py .`; exit 79 marks `[F] FAILED-INCOMPLETE` from the predicate, never from the session self-report.
  3. Outer loop on the terminal verdict: PASS → mark `[x]`. Findings-backed verdicts (NEEDS_WORK, verify/build-gate exhaustion) → amend the spec (recorded in the spec file), re-run — at most 3 outer iterations. Infrastructure / invalid-input / engine-availability / implement-empty BLOCKED verdicts are not spec-amendable → mark `[F] <verdict>` immediately.
  4. A blocked item never halts the queue; continue.
  5. When the queue is drained (or the session must stop), emit the drain report: per-item verdict, every logged assumption, and the commit range produced.

Strictly SERIAL — one `/devlyn:resolve` run at a time, never parallel. Never invent queue items, never reorder them, and never delete an item — only mark `[x]` / `[F]`.
