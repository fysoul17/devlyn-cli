The cleanup sentence is the right rung, and most of round 0 is in the draft. Three holes still let a false sentence qualify, or let ADOPT ship a regression.

Round 0 that is closed: scratch is "emptied"; resume says the receipt already records cleanup; `LOCAL_ONLY` names no commit; `FAILED` says nothing was published; `BLOCKED` is an explicit gap with no new sentence; `merge_refused` is applied before the sentence and is an unrepaired failed delivery; history is 4.2.18 motivation (rp-d3 INCONCLUSIVE, rp-d2 Y 0/2); the Claude slots are a four-category tripwire; the quote sentence, the second report sentence, the mirror rule, and the smoke consume/spare rule are frozen. The instruction diff against the `.agents` copy of `cbc33be9` is only that quote clause plus the deletion below. Token counts were not re-run here.

## HIGH

**1. Deleting the disposable-files sentence is a second change, and the helper sentence does not replace it.** The quote clause is the rung. The deletion is justified as "true by construction" (`DESIGN.md` lines 73–74). Construction fails wherever `cleanup` is absent. `main` still returns `BLOCKED` with only `reason` and `resume` (`task-complete.py:880–886`), including after `receipt["merge"]` is stored and `cleanup()` has already removed the worktree (`:827–830`, nested-repo test `:1598`). Scratch is emptied only inside `completion_result`, which that path never reaches, so owned scratch can still be full. The new report line tells the executor to quote `cleanup` on every result. Restore `No task is described as cleaned while owned disposable files remain.` Shorten the quote clause so the whole-file gate stays ≤ 4.2.22. State that verbatim quoting applies only when the field is present.

**2. Y smoke cannot entail "Removed" or "emptied".** Qualification uses the final resource record: worktree, registration, refs, scratch contents, directory (`DESIGN.md` lines 125–128). `github.py` `custody` has the same shape: absence is `worktree_exists` / `local_branch` / `remote_branch` / `scratch_files`, and an empty scratch list is still cleanup `COMPLETE`. Absence does not entail that this call deleted anything. A strict check rejects the true success sentence. A loose check accepts "Removed" for a resource that was already absent. Entailment has to use the action record this call writes: worktree removed, local ref deleted, remote ref deleted, scratch `CLEAN` / `RETAINED` / `NOT_OWNED`, `linked`, and whether `cleanup()` ran. Self-tests of those bits pass before pack. "Removed" and "emptied" are licensed only by those bits.

**3. ADOPT still ships a cost regression.** Category counts are nondecreasing, and that part of the round-0 gate is right. The cost line is not: each Y arm total may be 110% of X (`DESIGN.md` lines 160–161) and that result is a patch release. The ladder rule is that wall, input, and output per success must not increase (`NORTH-STAR.md:66–69`). On these ~450k-token runs, 10% is tens of thousands of tokens. Require owner seconds, input tokens, and output tokens for Y ≤ X, with UNKNOWN remaining a STOP. The four-slot noise stays in the interpretation limits.

## MEDIUM

**4. Two table sentences are broader than the facts the call has.**
- "the task worktree/branch was already gone" is one clause for three checks: `work.exists()`, `ref_sha`, and `remote_head` (`cleanup`, `:594–629`). Use one absent clause per resource: "task worktree was absent", "local task ref was absent", "remote task branch was absent".
- In-place is specified only on the `COMPLETE` row. `PR`, `PENDING`, `LOCAL_ONLY`, `FAILED`, and workspace `CLEANUP_PENDING` still say "task worktree" and, except `LOCAL_ONLY`, "branches". `linked` false never enters removal (`:594`); the checkout is unchanged (`task-completion.md` legacy paragraph). Those rows need "kept the in-place checkout", and `LOCAL_ONLY` has no remote branch.
- Copy the resume command from the object that owns it. Scratch retention stores `clean-scratch` (`:663–664`). Workspace retention stores its own `complete` command (`:833–834`). The result-level `resume` (`:656–657`) is a different command.

**5. `workspace_cleanup` key presence still means retention.** `retained = scratch RETAINED or "workspace_cleanup" in receipt` (`:670`), and success pops that key (`:630`). The action record needs its own key. Leaving the pop and line 670 as they are keeps a successful cleanup from becoming `CLEANUP_PENDING`.

**6. The decision branches overlap, and FALSE is undefined.** X cleanup ≥ 2/4 and Y cleanup ≤ 1/4 match both BASELINE MOVED and REJECT. First match wins: BASELINE MOVED, then REJECT, then MIXED. A Y category is FALSE when either reviewer says FALSE on any Y slot.

**7. The Claude guard is not pinned.** rp-d3 has no Claude arm, so inheritance does not name one. Pin Claude Code 2.1.296, `claude-opus-5-5`, effort `max`, the same pair rp-d1 and rp-d2 registered, plus the 6300 s auth floor already stated.

## LOW

**8. The opening delivery sentence covers rp-d3 m08.** That slot was graded and left its PR open (`rp-d3` `results.md`). The INCONCLUSIVE sentence later in the paragraph is the accurate one. Say every graded slot except rp-d3 m08 delivered.

VERDICT: REVISE
