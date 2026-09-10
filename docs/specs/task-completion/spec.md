---
id: task-completion
title: Finish owned tasks through PR merge and recoverable workspace cleanup
complexity: medium
---

# Finish owned tasks through PR merge and recoverable workspace cleanup

## Context and prediction

User observed dozens of residual worktrees after completed work and requests
handoff cleanup plus commit/push/PR/main merge before branch/worktree cleanup.
Live audit found 40 registrations: main, 29 inactive existing experiment/task
worktrees and 10 missing registrations. Research drivers and the outer agent
created these; production resolve does not allocate worktrees. Its CLEANUP
phase cleans source before VERIFY; mandatory archive stays inside the checkout.
The missing boundary is the outer owner's delivery and workspace lifecycle.

Prediction: explicit native Git/GitHub completion with prospective ownership,
exact verified source identity and external evidence custody will finish an
eligible task without leaving its owned workspace. PR mode and pending checks
will retain it visibly. It will neither publish a failed/unverified run nor
remove unrelated work. This is lifecycle correctness, not a claimed model
accuracy or token/speed improvement.

## Requirements

1. Add the smallest deterministic task-completion helper and canonical reference
   for the outer owner. Preserve the existing resolve phase graph, verdict,
   finish gate, archive authority and fresh workers. Call completion after the
   mandatory archive of a successful normal run; verify-only never publishes.
   Delivery failure/pending is separate from immutable product verification.
   Low-risk direct tasks use their actual decisive checks plus root acceptance
   of a scoped commit; never fabricate a pipeline result or require full resolve
   simply to ship. Explicit user local-only/no-push instructions take precedence.
2. Support project-local `git config --local devlyn.completionMode auto|pr`;
   absent means auto, invalid values fail visibly before external effects.
   Same two per-task overrides suffice. Auto means commit scoped task changes,
   push task branch, create/reuse a PR, request normal merge when requirements
   permit, then clean owned resources after actual merge. PR mode stops with
   the PR URL and preserves workspace. No extra approval ceremony when user
   scope already authorizes delivery; no bypass of repository protections.
3. Ownership is prospective and external to removable worktrees. A small receipt
   records common Gitdir, exact repo/remote/base/branch, original baseline,
   optional owned linked-worktree path/Gitdir, and task identity. Establish it
   through native creation of an absent explicitly named task branch and optional
   worktree; never adopt existing user/main/detached trees by name or prefix.
   Do not automatically create worktrees: normal in-place task branches suffice.
   Allocation is a bounded outer-owner step, not a scheduler or new resolve phase.
4. Before push bind the accepted commit and acceptance source into that receipt.
   A normal run requires its exact intended archived completed successful result,
   valid terminal report/finish evidence and `phases.cleanup.post_sha`, with no
   unverified product delta. Reuse existing validators where appropriate but
   terminal CLEAN alone does not imply PASS. Direct acceptance explicitly names
   the commit and checks/evidence accepted by the root; helper must not claim
   it independently proved those checks. Required terminal queue metadata is
   owner-only: handle the declared queue-file-only commit separately from the
   verified source, never accept an arbitrary descendant as implicitly verified.
   The helper need not stage product changes already committed by the pipeline.
5. Use Git and `gh`, no added dependency. Bind the intended GitHub repository,
   remote, base branch and source SHA; this task targets main. Push without force.
   Reuse PR only for the exact repository/head/base; validate remote head before
   merge. Native `gh pr merge --auto --merge --match-head-commit <sha>` respects
   required checks/reviews; no --admin, premature --delete-branch or strategy
   fallback. Unsupported policies fail visibly. Exit zero is not MERGED: query
   actual state and report pending with a resume command while retaining resources.
   A resumed completion inspects real Git/PR state and performs only missing
   effects, without duplicate PRs or new product verification. Protect concurrent
   completion calls with a per-receipt lock, not a universal worktree lease.
6. Only after actual matching MERGED evidence and source reachability may cleanup
   proceed. Preserve owned run/check evidence outside a removable checkout, with
   a file manifest and byte verification before removal. Retain recovery commit
   reachability. Revalidate exact ownership, registration/Gitdir, branch/head,
   clean tracked/untracked contents, ignored-content custody and writer cessation.
   Outer owner must wait its actual children and yield the tree; unknown foreign
   writers or caller cwd inside the target means retain with actionable guidance.
   A receipt/process scan is not a universal guarantee against future writers.
   Never delete main/default/detached/unowned/locked/changed/active trees or refs.
   Use native non-force worktree removal after valid custody; ref deletion needs
   exact expected-value guards, including remote branch race protection. An
   in-place main checkout is retained and safely returned to updated base before
   deleting its owned task branch. Cleanup retries after tree removal use the
   external receipt. No blind force deletion, killing processes or bulk pruning.
7. Document completion concisely in AGENTS.md/CLAUDE.md, README, resolve and queue
   outer-loop references, with canonical skill mirrors identical. Remove stale
   conflicting sentences before adding new prose. Installer/global permissions,
   engines, runtime state schema and version stay unchanged. Meaningful tests
   use real isolated Git repositories and a fake gh network boundary, not model
   calls or user remotes. No network mutation during these tests.
8. Replace the obsolete long autoresearch/HANDOFF.md with current continuation
   and next priorities, preserving original directive and historical links.
   Use the prepared handoff draft/audit under .devlyn/0143-worktree-shipping as
   data; update actual current-task status truthfully. Preserve historical 0139
   preparation unchanged, A16 user-parked custody, negative results and unadopted
   candidates. Legacy worktree inventory/archive/removal and final milestone
   record are separately executed by the owner, not by product phase workers.

## Authorized product surface

- config/skills/_shared/task-complete.py and .agents/skills/_shared/task-complete.py
- config/skills/devlyn:resolve/references/task-completion.md and its .agents mirror
- config/skills/devlyn:resolve/references/outer-loop.md and its .agents mirror
- config/skills/devlyn:resolve/SKILL.md and its .agents mirror
- config/skills/devlyn:queue/SKILL.md and its .agents mirror
- scripts/lint-skills.sh
- AGENTS.md, CLAUDE.md, README.md
- autoresearch/HANDOFF.md

The helper may embed its behavioral self-test following current shared-helper
practice. No generic registry, queue scheduler, background merge daemon, new
pipeline phase, old-experiment adoption, benchmark rerun or release publication.

<!-- devlyn:verification -->
## Verification

- `python3 config/skills/_shared/task-complete.py --self-test` exits 0 and tests
  real Git branch/worktree creation, PR versus auto policy, pending versus actual
  merge, exact-head races, PR reuse/retry, evidence recovery after removal and
  in-place branch cleanup. Unknown configuration, failed/verify-only product,
  unverified source descendants and foreign/dirty/locked/active workspaces must
  preserve files/refs and reject the prohibited effects. A declared queue-only
  owner commit is accepted without accepting unrelated source changes.
- Retry after push, PR creation, merge or worktree removal must finish only the
  missing eligible effects; concurrent completion must not duplicate those effects.
- Removing an owned completed worktree must preserve byte-identical archived
  evidence outside it; archive failure must retain the original tree and files.
- `bash scripts/lint-skills.sh` exits 0 with existing checks intact and the new
  helper integrated; source and installed mirrors remain identical.
- `git diff --check` exits 0. Independent source review checks verification,
  publication/ownership boundaries, failure recovery and handoff truthfulness.
