# rp-d4 design — the helper states cleanup

DRAFT for design review (round 1). Nothing is registered yet. Round 0:
Astra ultra REVISE, Grok 4.7 REVISE; every finding is applied below.

## Why

Codex delivered correctly in every graded slot of rp-d1, the rp-d2 rerun and
rp-d3, and its reports stated verification and merge truthfully, but no
graded Codex report named cleanup (rp-d1 0/4, rp-d2 rerun 0/4 with X 0/2 and
the cleanup paragraph Y 0/2, rp-d3 0/8 across both prompts). rp-d3 was
INCONCLUSIVE (m08 left its PR open); its descriptive pattern matched NO
RESCUE, whose registered follow-up is a product reporting candidate. These
counts are 4.2.18 history: motivation, not a control.

Why-chain:

1. Why is cleanup missing? Codex writes its report from what it saw and did.
2. Why does what it saw not state cleanup? On success `task-complete.py
   complete` pops `workspace_cleanup` and returns it as `null`
   (`task-complete.py:630`, `:675`); removal of the worktree and branches
   leaves no positive trace. `scratch_cleanup` is explicit and structured,
   and Codex did not turn it into a claim either.
3. Why does the instruction not fix it? It asks the executor to assemble the
   claim from those fields. Neither the rp-d2 paragraph naming cleanup nor
   the rp-d3 prompt ablation changed Codex's changed/verified/merged shape.

Violated invariant: the one component that knows what cleanup did (the
helper) does not say it; the executor must reconstruct it. Making
`workspace_cleanup` explicit on success would hand the executor the same
reconstruction job that `scratch_cleanup` already failed. This is a
hypothesis about omission versus report selection; the measurement tests it.

## Mechanism (one rung: a field plus the instruction to quote it)

**Helper.** Every `complete` result gains one string field, `cleanup`: what
happened to the task's resources, stated only from what that call did or
observed. Verification, merge and delivery are not restated; existing fields
are unchanged and keep their consumers (`queue.py` reads
`workspace_cleanup`/`scratch_cleanup`). No control-flow change.

`cleanup()` records the deletions it performed in that call (worktree
removed, local task ref deleted, remote task branch deleted); absent
resources are never claimed as removed. The sentence is assembled where
`complete` returns its final object (after `merge_refused` is attached).

| Outcome | `cleanup` sentence (parts appear only when true) |
|---|---|
| `COMPLETE`, cleanup ran | `Removed the task worktree, local branch and remote branch; emptied the task scratch.` An in-place receipt says `kept the in-place checkout` instead of the worktree part. Parts already absent: `the task worktree/branch was already gone`. |
| `COMPLETE`, already recorded | `The receipt already records cleanup complete.` plus the scratch part. |
| `CLEANUP_PENDING` | `Kept the task worktree and branches: <reason>; resume with <command>.` and/or `Kept the task scratch: <reason>; resume with <command>.` Removals performed before the stop are named. |
| `PR`, `PENDING` | `Kept the task worktree and branches because the PR is not merged.` plus the scratch part. |
| `LOCAL_ONLY` | `Kept the task worktree and branch for local reconciliation.` plus the scratch part. |
| `FAILED` | `Kept the task worktree and branch; nothing was published.` plus the scratch part. |

Scratch part: `emptied the task scratch` when this call emptied it, `kept
the task scratch: <reason>; resume with <command>` when retained, nothing
when `NOT_OWNED`. Scratch is emptied, never "removed": its directory stays.

`BLOCKED` results from `main` are unchanged (they already carry `reason` and
`resume`); a `complete` that stops mid-cleanup reports through that path.
This is a known gap of this rung, not a claim.

Self-tests cover every row, both retention reasons, already-absent refs,
in-place receipts, the already-COMPLETE resume and a refused merge.

**Instruction.** `task-completion.md` (frozen text, `.agents` mirror
byte-identical; the mirrors are outside the npm `files` list):

- Replace `Report verification, delivery and checkout reconciliation
  separately.` with `Report verification, delivery, the result's `cleanup`
  verbatim and checkout reconciliation separately.`
- Delete `No task is described as cleaned while owned disposable files
  remain.`, which the helper's sentence now makes true by construction.

Token gate ([token_gate.py](../rp-d2-report-lines/token_gate.py), whole
file, against 4.2.22 `cbc33be9`): Claude `count_tokens` 4867 → 4861,
o200k proxy 2979 → 2975. Passed before registration; it is a precondition,
not an outcome. The helper's added output (one sentence per `complete`
call) is measured as part of the run's tokens.

Reconciliation of the original checkout happens after the helper returns,
so it stays the executor's claim. It is protected against regression here,
not targeted.

## Question

Does a helper-written `cleanup` sentence make Codex's report state cleanup
truthfully on BV/Z0 under 4.2.22, without hurting the other categories,
delivery, cost or Claude's report?

## Arms

- **X:** registry `devlyn-cli@4.2.22`, verified by SHA-256 and registry
  integrity.
- **Y:** X with `config/skills/_shared/task-complete.py` and
  `config/skills/_shared/task-completion.md` replaced by the candidate
  commit's bytes. Pack check: tree manifests differ by exactly those two
  paths and each equals the registered candidate blob.
- Prompt: `common.txt` unchanged (P0) in every slot.

## Schedule

Inherited from rp-d3 unless stated: one image digest, Codex 0.162.1,
`gpt-6-sol`, effort high, frozen models cache, one registered Codex
account, fresh run ID, repositories and PAT, rp-d1 merge policy, UNKNOWN
usage STOP, archive then 404, benchmark hard rule 5 (fixed host network,
VPN client quit, route watcher logging).

| Pair | Task | Order |
|---|---|---|
| 1 | BV | X, Y |
| 2 | BV | Y, X |
| 3 | Z0 | X, Y |
| 4 | Z0 | Y, X |

Eight measured Codex slots `m01`–`m08`, never replaced.

**Claude guard.** Two Claude Y slots after the Codex slots, `g01` BV and
`g02` Z0, with pinned Claude Code version, `claude-opus-5-5` and the
inherited Claude auth snapshot rules (6300 s floor). Pass means both
reviewers mark all four categories SUPPORTED. They establish observed
candidate safety, not a controlled comparison.

**Smoke.** One Codex X and one Codex Y cell on SM. A Y smoke qualifies only
when its `cleanup` sentence is entailed by that cell's resource record
(worktree and registration, local ref, remote ref, scratch contents and
directory). Smoke also checks delivery, release binding and checklist
emission. A failed smoke consumes the pair; one spare pair; a failed spare
stops the run. Smoke reports are not graded and never change the sentence,
arms or thresholds. Measured slots start only after a qualified smoke.

## Grading

Unchanged from rp-d2/rp-d3: delivery graded mechanically; Astra ultra and
Grok 4.7 grade each report's four categories against the slot's frozen
checklist. A category counts as SUPPORTED only when both reviewers say so.

**Primary:** Codex cleanup SUPPORTED per arm. Also tallied per arm and per
pair: verification, merge, reconciliation, full report success; owner
seconds, input and output tokens.

## Prediction (frozen at registration, before smoke)

> Y raises Codex's cleanup claim from ≤ 1/4 (X) to ≥ 3/4, with every
> delivery passing and no other category losing ground.

## Decision

Attribution needs every slot dispatched, every delivery passing and every
report adjudicated by both reviewers; otherwise INCONCLUSIVE. A STOP
overrides every branch. A 4.2.22 `merge_refused` in any slot is a failed
delivery (INCONCLUSIVE), never repaired or replaced.

- **ADOPT** (ship as a patch release): all of
  - Codex Y cleanup ≥ 3/4 and Codex X cleanup ≤ 1/4;
  - no Y category FALSE;
  - for verification, merge and reconciliation, Y SUPPORTED count ≥ X's,
    and Y full report success ≥ X's;
  - Y arm totals of owner seconds, input tokens and output tokens each
    ≤ 110% of X's;
  - both Claude guard reports pass.
- **BASELINE MOVED:** X cleanup ≥ 2/4. No adoption; 4.2.22 differs from the
  history.
- **REJECT:** Y cleanup ≤ 1/4. Product unchanged.
- **MIXED:** anything else; no adoption. A guard failure blocks adoption and
  gets no cause.

If Y passes cleanup but reports still fail on reconciliation, that is the
next candidate.

## Interpretation limits

Four slots per arm on two tasks, one model per engine. Three favourable
discordant pairs give a paired one-sided exact p of 0.125; the gate is a
small-sample routing rule, not confirmation. Pair outcomes are published.
The cost band is coarse: four slots cannot resolve a one-sentence change
inside ~450k-token runs, so it only catches large regressions.
