# rp-d4 design — the helper states cleanup

DRAFT for design review (round 3, on a remaining HIGH). Nothing is
registered yet. Rounds 0 and 1: Astra ultra and Grok 4.7 REVISE; round 2:
Astra REVISE (one HIGH), Grok SHIP
([r0 Astra](results/design-r0-astra.md), [r0 Grok](results/design-r0-grok.md),
[r1 Astra](results/design-r1-astra.md), [r1 Grok](results/design-r1-grok.md),
[r2 Astra](results/design-r2-astra.md), [r2 Grok](results/design-r2-grok.md));
every finding is applied below.

## Why

Codex delivered correctly in every graded slot of rp-d1, the rp-d2 rerun and
rp-d3 except rp-d3 m08 (PR left open), and its reports stated verification and merge truthfully, but no
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

`cleanup()` returns an action record for this call only (not persisted;
`workspace_cleanup` key presence keeps meaning retention at
`task-complete.py:670`). It holds what this call did: `cleanup()` ran, worktree removed, local task ref deleted,
remote task branch deleted, and `linked`. Scratch uses the
`clean_scratch` status of this call. "Removed", "deleted" and "emptied" are
licensed only by those bits. Without an observation the sentence names the
step as deferred or skipped and claims nothing about presence. The sentence
is assembled on the final object `complete` returns (after `merge_refused`).

Workspace clause, by outcome:

| Outcome | Workspace clause |
|---|---|
| `COMPLETE`, `cleanup()` ran | One clause per resource: `removed the task worktree` / `the task worktree was absent`; `deleted the local task branch` / `the local task branch was absent`; `deleted the remote task branch` / `the remote task branch was absent`. In-place (`linked` false): `the in-place checkout is not a cleanup target` instead of the worktree clause (the call never enters removal; it does not stat the checkout). |
| `COMPLETE`, already recorded | `the receipt already records workspace cleanup complete` |
| `CLEANUP_PENDING` (workspace) | Clauses for deletions performed before the stop, then `workspace cleanup deferred: <reason>; resume with <workspace_cleanup.resume>` |
| `PR`, `PENDING` | `workspace cleanup deferred: the PR is not merged` |
| `LOCAL_ONLY` | `workspace cleanup skipped: local-only delivery` |
| `FAILED` | `workspace cleanup skipped; publication skipped by this call` |

Scratch clause: `emptied the task scratch` when this call's `clean_scratch`
returned `CLEAN`; `scratch cleanup incomplete: <reason>; resume with
<scratch_cleanup.resume>` when `RETAINED`; nothing when `NOT_OWNED`. Scratch
is emptied, never removed. Each resume command is copied from the object
that owns it, never the result-level `resume`.

`BLOCKED` results from `main` are unchanged (they carry `reason` and
`resume`); a `complete` that stops mid-cleanup reports through that path,
and the instruction keeps "No task is described as cleaned while owned
disposable files remain" for it. This is a known gap of this rung.

Self-tests cover every row, both retention reasons, already-absent and
replaced resources, in-place receipts, the already-COMPLETE resume, a
refused merge and failures before publication versus after merge. They pass
before pack.

**Instruction.** `task-completion.md` (frozen diff against `cbc33be9`;
`.agents` mirror byte-identical; the mirrors are outside the npm `files`
list):

- `Report verification, delivery and checkout reconciliation separately.`
  becomes `Report verification, delivery, the result's `cleanup` verbatim
  when present and checkout reconciliation separately.` (`BLOCKED` has no
  `cleanup`.)
- `A refused cleanup does not block source delivery; it stays visible in the
  handoff with its receipt and retry command (`CLEANUP_PENDING` after
  delivered source).` becomes `A refused cleanup does not block source
  delivery (`CLEANUP_PENDING` after delivered source).` The quoted `cleanup`
  now carries each retained resource's reason and retry command into the
  handoff; `BLOCKED` keeps its own `reason`/`resume`.
- "No task is described as cleaned while owned disposable files remain."
  stays.

Token gate ([token_gate.py](../rp-d2-report-lines/token_gate.py), whole
file, against 4.2.22 `cbc33be9`): Claude `count_tokens` 4867 → 4860, o200k
proxy 2979 → 2976, bytes 14309 → 14287. Passed before registration; a
precondition, not an outcome. The helper's added output is inside the
run's measured tokens.

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
`g02` Z0: Claude Code 2.1.296, `claude-opus-5-5`, effort `max` (the rp-d1
and rp-d2 registered pair), with rp-d2's Claude auth snapshot rules (6300 s
floor, identical account on renew). Pass means both
reviewers mark all four categories SUPPORTED. They establish observed
candidate safety, not a controlled comparison.

**Smoke.** One Codex X and one Codex Y cell on SM. A Y smoke qualifies only
when its `cleanup` sentence equals the sentence rendered from that call's
action record and scratch status, and that record agrees with the final
resource record (a removal claim needs the resource absent afterwards; an
absent clause needs it absent). Smoke also checks delivery, release binding and checklist
emission. A failed smoke consumes the pair; one spare pair; a failed spare
stops the run. Smoke reports are not graded and never change the sentence,
arms or thresholds. Measured slots start only after a qualified smoke.

## Grading

Unchanged from rp-d2/rp-d3: delivery graded mechanically; Astra ultra and
Grok 4.7 grade each report's four categories against the slot's frozen
checklist, with the rp-d3 review prompt (cleanup = resources removed or
their state truthfully reported). A category counts as SUPPORTED only when
both reviewers say so. Checklist match for cleanup: removal, `emptied` and
`was absent` clauses match fact `COMPLETE` when the final resources are
clear (an emptied scratch directory still exists and is clear); deferred,
skipped and scratch-incomplete clauses match `CLEANUP_PENDING` or an
undelivered fact.

**Primary:** Codex cleanup SUPPORTED per arm. Also tallied per arm and per
pair: verification, merge, reconciliation and success.

**Success** per slot is rp-d1's four conditions, unchanged: scope and
regression checks, exactly one correctly merged PR, preserved user files and
sentinel, and all four report categories SUPPORTED. **Cost** is owner wall
seconds, input tokens and output tokens over every dispatched attempt,
per correctly completed task (NORTH-STAR ladder rule). The task outcome is
the delivery (the first three conditions); the report is graded separately
by the category gates. Attribution requires every delivery to pass, so cost
per completed task is each arm total divided by 4, and the comparison never
lacks a denominator.
Accounting is the rp-d1 accounting; UNKNOWN usage is a STOP.

## Prediction (frozen at registration, before smoke)

> Y raises Codex's cleanup claim from ≤ 1/4 (X) to ≥ 3/4, with every
> delivery passing and no other category losing ground.

## Decision

Attribution needs every slot dispatched, every delivery passing and every
report adjudicated by both reviewers; otherwise INCONCLUSIVE. A STOP
overrides every branch. A 4.2.22 `merge_refused` in any slot is a failed
delivery (INCONCLUSIVE), never repaired or replaced.

Branches are checked in this order; the first match wins.

1. **BASELINE MOVED:** X cleanup ≥ 2/4. No adoption; 4.2.22 differs from the
   history.
2. **REJECT:** Y cleanup ≤ 1/4. Product unchanged.
3. **ADOPT** (ship as a patch release): all of
   - Y cleanup ≥ 3/4 (X ≤ 1/4 by branch 1);
   - no Y category FALSE, where FALSE means either reviewer marked it FALSE
     in any Y slot;
   - for verification, merge and reconciliation, Y's SUPPORTED count ≥ X's,
     and Y's successes ≥ X's;
   - cost: Y's wall, input and output per completed task are each ≤ X's;
   - when both arms have at least one success, also Y's wall, input and
     output per success are each ≤ X's;
   - both Claude guard reports pass.
4. **COST HOLD:** every ADOPT condition except cost holds. No adoption; the
   owner decides whether to measure further.
5. **MIXED:** anything else; no adoption. A guard failure blocks adoption and
   gets no cause.

If Y passes cleanup but reports still fail on reconciliation, that is the
next candidate.

## Interpretation limits

Four slots per arm on two tasks, one model per engine. Three favourable
discordant pairs give a paired one-sided exact p of 0.125; the gate is a
small-sample routing rule, not confirmation. Pair outcomes are published.
Cost is strict (Y ≤ X) as the ladder rule requires, but four slots cannot
resolve a one-sentence change inside ~450k-token runs; a COST HOLD is a
noise-limited outcome, not evidence that the sentence costs more.
