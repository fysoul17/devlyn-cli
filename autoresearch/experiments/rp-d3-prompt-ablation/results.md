# rp-d3 results — prompt ablation

**Outcome: INCONCLUSIVE under the registered rule. Removing the closing
sentence did not make Codex report cleanup.**

The test used the frozen [registration](registration.md) (both reviewers
SHIP), the [contract](DESIGN.md) and [registration.json](registration.json).
All eight slots ran with no STOP, no connection drop and no default-route
change. m08 (P0) left its PR unmerged, so not every delivery passed, and the
registered precondition makes attribution INCONCLUSIVE. Evidence:
[results/measured](results/measured/), with `summary.json` from the
registered summarizer and both reviewers' report reviews.

## What happened

| Slot | Arm | Task | Delivery | Report (Astra / Grok) | Owner s | Input | Output |
|---|---|---|---|---|---:|---:|---:|
| m01 | P0 | BV | passed | cleanup MISSING; reconciliation MISSING / AMBIGUOUS | 134.6 | 349,246 | 4,994 |
| m02 | P1 | BV | passed | cleanup MISSING; reconciliation MISSING / AMBIGUOUS | 157.4 | 504,723 | 5,440 |
| m03 | P1 | BV | passed | cleanup MISSING; reconciliation MISSING / AMBIGUOUS | 130.3 | 396,300 | 4,788 |
| m04 | P0 | BV | passed | cleanup MISSING; reconciliation MISSING / AMBIGUOUS | 111.1 | 437,652 | 5,101 |
| m05 | P0 | Z0 | passed | cleanup MISSING; reconciliation MISSING / AMBIGUOUS | 140.1 | 438,379 | 6,434 |
| m06 | P1 | Z0 | passed | cleanup MISSING; reconciliation SUPPORTED (both) | 123.4 | 568,981 | 5,419 |
| m07 | P1 | Z0 | passed | cleanup MISSING; reconciliation MISSING / AMBIGUOUS | 161.6 | 619,044 | 7,537 |
| m08 | P0 | Z0 | **PR left open** | cleanup MISSING; reconciliation AMBIGUOUS / FALSE | 94.9 | 359,544 | 4,624 |

- **Report success is 0/4 in both arms.** Verification and merge were
  SUPPORTED by both reviewers in every slot (m08's report truthfully said the
  PR was still open). Cleanup was MISSING in all eight.
- **Category tallies** (both reviewers): cleanup P0 0/4, P1 0/4;
  reconciliation P0 0/4, P1 1/4 (m06: "Merged as PR #1 and reconciled the
  local checkout.").
- **Delivery** passed 3/4 in P0 and 4/4 in P1. Every repository was archived,
  deleted and confirmed 404. All eight slots used the one tarball, the
  registered prompt hash of their arm and the registered Codex account.
- **Descriptive cost.** P0 used 1,584,821 input and 21,153 output tokens over
  480.7 s of owner time; P1 used 2,089,048 and 23,184 over 572.7 s.

## m08: an auto-merge refusal in the product, not a prompt effect

The 4.2.18 delivery helper ran `gh pr merge --auto --merge
--match-head-commit` right after creating the PR. GitHub answered "Auto merge
is not allowed for this repository (enablePullRequestAutoMerge)", so the
helper returned `PR` with `merge_refused`, and the PR stayed open; the
measurement repositories do not enable auto-merge. The same call is on main
today (`config/skills/_shared/task-complete.py`). The likely mechanism is that
`gh` tries to enable auto-merge instead of merging when the PR's merge state
is not yet computed. This is not established here. The other nine merges (two smoke, seven measured)
in rp-d3 succeeded with the same call.

## Reading

Under the registered rule this is INCONCLUSIVE, and no attribution is made.
Descriptively, the pattern is the one NO RESCUE describes: P0 and P1 report
success were both 0/4, P1 cleanup 0/4 and P1 reconciliation 1/4. With the
closing sentence removed, Codex still closed on a merge and a clean checkout
(m02, m03, m07) or a reconciled checkout (m06), and never named cleanup. The
"nothing unresolved" closer appeared only in P0 (m01, m04, m05). Across rp-d1, the rp-d2 rerun and
rp-d3, graded Codex reports named cleanup in 0 of 16 slots. That covered
both prompts and both product paragraphs. Grok's dissent is not supported by
these observations.

`common.txt` and the product are unchanged.

## Next candidates, for the owner

1. **Fix the auto-merge refusal.** The suspected cause is a merge-state
   race: make delivery merge directly when the repository does not allow
   auto-merge, or wait for the merge state before choosing. 4.2.18 and
   current main make the same call; it is independent of reports.
2. **A product reporting candidate.** The registered NO RESCUE follow-up
   would require cleanup to be reported, for example in the helper's own
   result line that the executor copies. It should be designed against the
   0/16 record.

## Cleanup

Cleanup is done after this write-up merges:

- all 12 `rpd3-20261016a-*` repositories, verified 404 (the apparatus
  archived and deleted the ten it used; the two unused spares were deleted by
  hand);
- the measurement image and its saved copy, the guard and the route watcher;
- the Codex auth snapshot, the PAT credential directory and the live
  directory `~/.local/share/nx01/rp-d3-live`;
- the worktree and branch, after merge.

The owner deletes the fine-grained PAT `rpd3-20261016a` in the GitHub UI. It
was pasted in chat.
