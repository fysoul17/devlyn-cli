# rp-d4 design — the helper writes the delivery report sentence

DRAFT for design review (round 0). Nothing is registered yet.

## Why

Across rp-d1, the rp-d2 rerun and rp-d3, graded Codex reports named cleanup
in 0 of 16 slots ([rp-d3 results](../rp-d3-prompt-ablation/results.md)).
Codex delivered correctly every time and its reports stated verification and
merge truthfully. Neither instruction-only rung changed the cleanup gap:
the rp-d2 product paragraph that names cleanup (Y) and the rp-d3 prompt
ablation (P1) both stayed at 0/4. rp-d3's NO RESCUE branch names the next
rung: a product reporting candidate. Claude passed every graded report
(rp-d1 3/3, rerun 3/3).

Why-chain, from the evidence:

1. Why is cleanup missing? Codex writes its report from what it saw and did.
2. Why does what it saw not include cleanup? On success `task-complete.py
   complete` returns `"workspace_cleanup": null` (the field is popped once
   cleanup succeeds); worktree, branch and remote-branch removal leave no
   positive trace in the result. Only `scratch_cleanup` is explicit, nested
   among a dozen other keys.
3. Why does the instruction not fix it? The instruction asks the executor to
   assemble the claim from those fields; Codex's report keeps a short
   changed/verified/merged shape whatever the paragraph or prompt says.

The violated invariant: the only component that knows the cleanup outcome
(the helper) does not state it. The executor is asked to reconstruct it.

## Mechanism (one rung)

1. **Helper.** Every `complete` result (and its `BLOCKED` error result) gains
   one field, `report`: one plain English sentence built only from facts the
   helper observed in that call. Examples:
   - `COMPLETE`: `Merged <pr url>; removed the task worktree, task branch
     and scratch.` (Each part only when that resource existed and was removed;
     an in-place receipt has no worktree.)
   - `CLEANUP_PENDING`: `Merged <pr url>; kept <resource> because <reason>;
     resume with <command>.`
   - `PR`: `Opened <pr url>; not merged because <merge_refused | mode pr>;
     the task worktree is kept until it merges.`
   - `PENDING`: `<pr url> waits for auto-merge; the task worktree is kept;
     resume with <command>.`
   - `LOCAL_ONLY`: `Committed <sha> on <branch> only; no push, PR or merge.`
   - `FAILED`: `Verification failed; nothing was delivered.`
   - `BLOCKED`: `Delivery blocked: <reason>; resume with <command>.`
   The existing fields are unchanged. No new behavior, only a new field.
2. **Instruction.** `task-completion.md`'s reporting paragraph replaces
   "Report verification, delivery and checkout reconciliation separately."
   with a sentence that asks for verification, checkout reconciliation and
   the completion result's `report` quoted verbatim. The token gate
   ([rp-d2 token_gate.py](../rp-d2-report-lines/token_gate.py)) must show no
   increase for the whole file (Claude `count_tokens`, o200k proxy for
   Codex). The `.agents` mirror is identical.

Reconciliation of the original checkout happens after the helper returns
(the executor's own `git merge --ff-only`), so the helper cannot state it.
It stays the executor's claim. This rung targets cleanup only.

## Question

Does a helper-written `report` sentence make Codex's final report state
cleanup truthfully on BV/Z0, without hurting delivery or Claude's report?

## Arms

- **X (control):** registry `devlyn-cli@4.2.22` tarball, verified by SHA-256
  and registry integrity.
- **Y (candidate):** the same tarball with exactly the two product files
  (`task-complete.py`, `task-completion.md`) replaced by the candidate commit.
  The pack check confirms the trees differ by exactly those two files.
- Prompt: `common.txt` unchanged in both arms (P0).

## Schedule

Codex 0.162.1, `gpt-6-sol`, effort high, rp-d1/rp-d2 image definition.
Tasks BV and Z0, two repetitions each, paired and interleaved (X,Y / Y,X /
X,Y / Y,X), eight measured slots `m01`–`m08`, never replaced.

**Claude guard.** Two Claude Y slots (`g01` BV, `g02` Z0) after the Codex
slots. Claude's report passed 6/6 historically under X; the guard checks
that a quoted sentence does not break it. (Open question for review: keep
the guard, or move it to a release check.)

Smoke: one Codex X and one Codex Y cell on SM, one spare pair. Smoke checks
delivery, the release binding, the presence of `report` in Y's helper
output and checklist emission. Smoke reports are not graded.

## Grading

Unchanged from rp-d2/rp-d3: delivery graded mechanically; Astra ultra and
Grok 4.7 grade each report's four categories against the slot's frozen
checklist. **Primary metric: cleanup SUPPORTED by both reviewers**, per arm.
Report success (all four) and reconciliation are tallied descriptively.

## Prediction (frozen at registration, before smoke)

> Y raises Codex's cleanup claim from ≤ 1/4 (X) to ≥ 3/4, with every
> delivery passing.

## Decision

Attribution needs every slot dispatched, every delivery passing and every
report adjudicated by both reviewers; otherwise INCONCLUSIVE. A STOP
overrides every branch.

- **ADOPT:** Codex Y cleanup ≥ 3/4, Codex X cleanup ≤ 1/4, no Y category
  FALSE, both Claude guard reports pass, token gate passes. Ship Y as a
  patch release.
- **REJECT:** Codex Y cleanup ≤ 1/4. Product unchanged.
- **MIXED:** anything else; no adoption.

Reconciliation is out of scope; if Y reports still fail only on
reconciliation, that is the next candidate.

## Interpretation limits

Four slots per arm on two tasks, one model per engine. 3/4 vs 0/4 has a
one-sided Fisher p of about 0.07; the gate routes, it does not prove.
