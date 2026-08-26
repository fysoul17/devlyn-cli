---
complexity: medium
---

# Harness artifact-integrity seal

The post-planning loop cannot be sealed while one task run can consume a stale
verification patch or start from tracked owner edits that its finish gate may absorb or
revert. This spec closes only those live artifact-integrity failures. Project-plan queue
seeding and aggregate project closure remain the next feature.

## Evidence

- 'config/skills/_shared/resolve-bootstrap.py' writes
  '.devlyn/external-diff.patch' only for '--verify-only'; its atomic batch deletes a file
  only when the caller explicitly owns that key with None.
- 'config/skills/_shared/spec-verify-check.py' consumes an existing
  '.devlyn/external-diff.patch' without a mode check, so a later spec/free-form run can
  inherit stale verify-only bytes.
- 'config/skills/_shared/finish-gate.py' calculates changed tracked files from the
  bootstrap base SHA and can revert files outside the authorized surface. A full run
  bootstrapped on tracked owner edits therefore has a dishonest base and a data-loss
  path.
- '/devlyn:queue' drains items serially into '/devlyn:resolve'; its current contract does
  not first make queue/spec artifacts part of a committed baseline.

## Subtractive-first decision

1. Make bootstrap own the existing external-patch artifact in every mode; add no second
   reader-side mode defense.
2. Reject a dishonest full-run baseline before any bootstrap write; do not weaken the
   finish gate with an exemption.
3. Amend the serial queue/outer-loop commit discipline; add no flag, wrapper, recovery
   branch, or new artifact.

## Requirements

### R1 — external patch lifecycle has one owner

1. 'resolve-bootstrap.py' includes '.devlyn/external-diff.patch' in every atomic output
   batch.
2. '--verify-only' writes the exact captured external diff as today.
3. spec and free-form modes pass None for that output so a stale patch is deleted before
   their state is published.
4. Add red-first self-test coverage that pre-seeds stale bytes and proves both full modes
   remove them while verify-only preserves exact bytes.
5. Do not add a mode branch to 'spec-verify-check.py'; bootstrap is the artifact owner.

### R2 — full runs require an honest tracked baseline

1. Before writing any '.devlyn' output, spec and free-form modes inspect both index and
   working-tree tracked changes.
2. Any tracked change outside '.devlyn' fails closed with 'BLOCKED:worktree-dirty',
   names actionable commit/stash guidance, and leaves all bootstrap output bytes
   unchanged.
3. '--verify-only' is exempt because its external diff is the input under verification.
4. Untracked files remain allowed because the existing untracked-baseline manifest owns
   that contract. Tracked changes confined to '.devlyn' remain allowed.
5. Add red-first self-tests for staged, unstaged, '.devlyn'-only, untracked, and
   verify-only cases.

### R3 — serial queue and outer loop preserve the new invariant

1. Before each full '/devlyn:resolve', the queue/outer-loop contract requires the exact
   queue item, linked spec bundle, and any accepted spec amendment to be committed in a
   scoped commit.
2. After a terminal item result, its '[x]' or '[F]' queue transition is committed before
   the next pending item starts.
3. A failed verification amendment is committed before rerunning that item.
4. Apply the contract consistently to canonical 'config/skills' sources and the tracked
   '.agents' mirror, plus top-level 'AGENTS.md' and 'CLAUDE.md' where the repository
   workflow is defined. Do not edit ignored '.claude/skills' installation output.
5. Do not add queue parallelism, plan parsing, automatic commits in bootstrap, or a
   project-level closure judge.

## Red-first obligation

Before changing production logic, add the self-test assertions for R1 and R2 and retain
their raw failing result in the resolve run evidence. Then implement the smallest change
and rerun green.

## Non-goals

- '/devlyn:queue add-plan', project plan schema, topological seeding, intent digest, or
  aggregate project acceptance.
- Any finish-gate relaxation or spec-file exemption.
- Any change to 'spec-verify-check.py' artifact selection.
- Runtime task decomposition, concurrent drains, or devlynd completion truth (RT-21).
- New dependencies or user-facing flags.

## Authorized implementation surface

- 'config/skills/_shared/resolve-bootstrap.py'
- '.agents/skills/_shared/resolve-bootstrap.py'
- 'config/skills/devlyn:queue/SKILL.md'
- '.agents/skills/devlyn:queue/SKILL.md'
- 'config/skills/devlyn:resolve/references/outer-loop.md'
- '.agents/skills/devlyn:resolve/references/outer-loop.md'
- 'AGENTS.md'
- 'CLAUDE.md'
