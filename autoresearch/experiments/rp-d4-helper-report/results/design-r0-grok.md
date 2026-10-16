The root cause is right, and a helper-written sentence is the right rung. The draft sentences are not all true from the facts that call has, and the adoption rule can ship a regression. Do not register this yet.

Codex omitted cleanup in 0/16 graded slots while delivery itself cleaned up. Naming cleanup in the product paragraph and deleting the prompt closer both stayed at 0/4. On success, `cleanup` pops `workspace_cleanup` and `completion_result` returns it as null (`task-complete.py:630`, `:675`). `scratch_cleanup` is already an explicit structured field, and Codex did not turn it into a cleanup claim. A positive `workspace_cleanup` object would hand the executor the same reconstruction job. Deleting the pop, or deleting the reporting paragraph, does not put a cleanup sentence in the final report. The matching rung is one sentence built from effects this call performed, plus one instruction to quote it. Those two edits are one rung.

The paired schedule (X,Y / Y,X / X,Y / Y,X on BV, BV, Z0, Z0), the primary metric (cleanup SUPPORTED by both reviewers), and the 3/4 vs ≤1/4 routing gates are sound. Reconciliation staying descriptive is sound.

## HIGH

**1. The example sentences assert actions the return site cannot see.** `completion_result` does not record what this call deleted. `merge_refused` is attached after `result("PR")` returns (`:826`). `main`'s `BLOCKED` handler (`:880-886`) sees only the exception. Pin an action record from `cleanup` — `worktree_removed`, `local_branch_removed`, `remote_branch_removed` — for deletions this call performed. Assemble `report` on the object `complete` actually returns. Cover every row with a self-test.

| Path | Fact in that call | Draft problem | Truthful shape |
|---|---|---|---|
| Linked `COMPLETE` | Worktree removed only if `linked` and it existed (`:594`). Remote ref deleted only when `remote == sha` (`:621-626`). Scratch is emptied; the directory stays (`:538`, `:560-566`). | "removed … scratch". "task branch" merges local and remote. | "Merged \<url\>; removed the linked worktree and \<refs this call deleted\>; emptied scratch." |
| In-place | `linked` is false. The checkout is never modified (`task-completion.md:228-229`). `receipt["worktree"]` is the anchor. | "an in-place receipt has no worktree" | "Merged \<url\>; retired \<refs this call deleted\>; checkout kept; emptied scratch." |
| Remote already absent | Delete is skipped. | Claiming the remote branch was removed. | Omit the remote clause. |
| Scratch `NOT_OWNED` | Default when `scratch_identity` is absent (`:540-541`, `:658`). | "removed scratch" | Omit scratch. |
| Already-`COMPLETE` resume | `:743-745` does not call `cleanup`. Absence is visible; removal is not. | "removed the task worktree…" | "Already complete; \<url\>; linked worktree absent; \<refs absent\>; scratch \<clean or kept\>." |
| `CLEANUP_PENDING` | Workspace can be retained before any deletion (`:829-836`), or scratch retained after a successful cleanup, or both. | One "kept \<resource\>" | Name each kept resource with its own reason and resume. Name a removal only from the action record. |
| `PR` | Mode `pr` returns at `:786` with no `merge_refused`. A refusal is wrapped on afterward (`:826`). The PR may already have existed (`:753-758`). | Sentence inside `completion_result`. "Opened". "because merge_refused" on a mode-`pr` return. | Mode `pr`: "PR \<url\> is open; not merged in pr mode; linked worktree kept." Refusal: "PR \<url\> is open; not merged because \<refused\>; linked worktree kept." |
| `PENDING` | Status does not mean auto-merge. | "waits for auto-merge" whenever status is `PENDING`. | "PR \<url\> is not merged yet; linked worktree kept; resume with \<resume\>." Add "auto-merge is requested" only when `autoMergeRequest` is present. |
| `LOCAL_ONLY` | Push is refused (`:728-729`). A SHA exists only after acceptance is bound. The helper does not commit. | "Committed \<sha\>" with no bound SHA. | "Local only on \<branch\> at \<sha\>; no push, PR, or merge." Omit the SHA when none is bound. |
| `FAILED` | Loop `verdict == FAILED` (`:725-726`, `:327-329`). Nothing is published. | "Verification failed" | "Result verdict is FAILED; nothing was published." |
| `BLOCKED` from `main` | Reason and, for `complete`, resume. Merge may already be stored: `cleanup` raises `CompletionError` after `receipt["merge"]` is written (`:827-830`; nested-repo test `:1598`). | "Delivery blocked" plus a resume command on every `BLOCKED`. | For `complete` only, re-read the receipt. If `merge` is recorded: "Complete stopped after merge: \<reason\>; workspace still present; resume with \<resume\>." Otherwise: "Complete stopped: \<reason\>; resume with \<resume\>." Leave allocate and clean-scratch unchanged. Do not change control flow in this rung. |

**2. ADOPT can ship a Codex regression, and the Claude gate is undefined.** Verification and merge were SUPPORTED on every graded Codex slot across rp-d1, the rp-d2 rerun, and rp-d3. A quote instruction can make Codex emit only `report`. `MISSING` is not `FALSE`, so ADOPT still fires. "Both Claude guard reports pass" does not say who grades them or which categories count.

Keep the two Claude Y slots as a fail-closed tripwire. A later release check is too late for an instruction change. Require, on every Codex Y slot, verification and merge SUPPORTED by both reviewers. Keep reconciliation as a descriptive tally. Define a guard pass as both reviewers marking all four categories SUPPORTED on the same rubric. Two passes are a tripwire: there is no paired Claude X, one slot per task, and the 6/6 history is 4.2.18 under the old paragraph. A guard failure blocks adoption and gets no cause.

**3. The quote instruction is half the rung and is not frozen.** The field is what the executor copies. The sentence at `task-completion.md:203` is what tells it to copy. That sentence is unspecified, so the token gate cannot be checked and the treatment is not frozen.

Put the exact replacement for the first sentence in the design. Keep the second sentence (a delivery error does not rewrite an accepted product result). Show the whole-file token table, Claude `count_tokens` and the o200k proxy, both less than or equal to the 4.2.22 file. State that a positive result belongs to the pair. Name the tarball paths `config/skills/_shared/task-complete.py` and `task-completion.md`. Keep the `.agents` mirrors byte-identical in the commit. They are outside the npm `files` list, so they are not the measured artifact.

## MEDIUM

**4. The 0/16 history is 4.2.18. The control is 4.2.22.** The success payload still has `workspace_cleanup: null`, so the missing-prose mechanism carries. The cleanup base rate does not. 4.2.22 still returns `PR` with `merge_refused` when auto-merge is off and the merge state stays outside `CLEAN` / `HAS_HOOKS` / `UNSTABLE`, or `UNKNOWN` through the poll (`:815-826`). One such slot fails "every delivery passing" and makes the run INCONCLUSIVE, which is what rp-d3 m08 did. Write both limits. Treat `X` cleanup ≥ 2/4 as "the 4.2.22 baseline moved," and leave Y unadopted. Do not repair or replace the slot.

**5. Smoke checks that `report` is present.** A false sentence passes that check. Qualify Y smoke only when the sentence is entailed by that cell's resource record: worktree, registration, local ref, remote ref, scratch files, and the scratch directory still present. Leave smoke reports ungraded. Smoke must not change the sentence, the arms, or the thresholds. An unqualified spare stops the run. Measured slots stay irreplaceable and start only after a qualified smoke.

**6. The apparatus is unnamed.** Grading is "unchanged," and a STOP overrides, but the draft does not inherit rp-d3's frozen image digest, CLI pin, account, fixed route, UNKNOWN-usage STOP, or archive-then-404. Without those, a dropped connection or an account change is indistinguishable from the rung.

## LOW

**7. The token gate is a pre-registration check.** Take it out of the ADOPT branch so a wording failure is not recorded as a measured outcome.

**8. Record owner time and input and output tokens per arm, descriptively.** rp-d3 did this. No cost gate unless the owner adds one.

**9. `completion_result` also builds `reconcile` rows.** The same action record has to stay truthful there. Those rows are informational.

VERDICT: REVISE
