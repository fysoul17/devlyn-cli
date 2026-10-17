The MIXED decision matches the registered order and `summary.json`. The write-up still misstates the guard reports, so it should be revised before it becomes the record.

## HIGH

**Guard quote attribution is false.** `results.md` says g02 quoted the helper sentence and g01 described the same state in its own words. Both final reports quote it. g01 says: `The helper's cleanup report, verbatim: "Removed the task worktree; deleted the local task branch; deleted the remote task branch; emptied the task scratch."` g02 says: `The helper's cleanup report: "Removed the task worktree; deleted the local task branch; deleted the remote task branch; emptied the task scratch."` Both reviewers mark both SUPPORTED. The load-bearing guard result (both passed all four categories) is right; this sentence about how they passed is wrong.

## MEDIUM

**The Reading, and HANDOFF line 3, treat m02 as carrying the sentence.** The results bullet is exact: m07 quotes `Cleanup: Removed the task worktree; deleted the local task branch; deleted the remote task branch; emptied the task scratch.` m02 paraphrases `Delivery cleanup removed the task worktree and branches and emptied its scratch directory.` The Reading then says Codex carried the helper's sentence in half the Y reports. HANDOFF line 3 says the same ("the two Y reports that carried the sentence"). The rp-d4 paragraph later in HANDOFF is exact (m07 verbatim, m02 paraphrase).

**"The mechanism moves Codex" overclaims the same page's test.** Two favourable discordant pairs and zero unfavourable pairs give one-sided exact p = 0.25, and the Decision section already says that is not distinguishable from noise. The gate miss and the replication-or-stop choice are the honest reading.

## LOW

**"fast-forwarded" is exact only for m02.** m02 says `fast-forwarded`. m07, and both reviewers' reconciliation quotes, say `fast forwarded`. Both reconciliation findings are still SUPPORTED.

## Checked, and holding

- Table arms, tasks, deliveries, findings, token counts, and one-decimal times match `summary.json`. Arm totals are X 2,264,753 / 21,286 / 512.6 s and Y 1,581,115 / 20,458 / 425.8 s.
- Ordered rules: no STOP, no `merge_refused`, usage COMPLETE, deliveries 10/10, so not INCONCLUSIVE. X cleanup 0/4 skips BASELINE MOVED. Y cleanup 2/4 skips REJECT. ADOPT fails only on Y cleanup ≥ 3/4. Verification and merge are 4/4 in both arms; reconciliation is 0/4 and 2/4; successes are 0/4 and 2/4; no FALSE; guards pass; cost passes by dominance with strict improvement because S_Y > S_X. That is MIXED, which matches `summary.json`.
- m03, m06, and the Y smoke report omit cleanup. Codex `api_errors` and `stream_retries` are empty. `route-watch.log` has no interface change after `2026-10-17T02:07:25Z` (`en0` → `none` → `en0` only).
- Prior graded Codex successes are 0 in rp-d1, the rp-d2 rerun, and rp-d3. The two next options (same candidate, more pairs, or stop) match a 2/4 vs 0/4 result.
- Committed measured evidence has no PAT, bearer, VPN hostname, or IP. The route log names `en0` and `none`. Account-id prefixes and the PAT name `rpd4-aa` are identifiers already in the registration.
- This session has no shell, so `git diff cbc33be9 -- config .agents` was not executed. On disk, both `task-completion.md` copies still have the baseline report line and the handoff clause, and `completion_result` still returns `workspace_cleanup` with no cleanup sentence. The worktree was created from `main` at `cbc33be9`.

VERDICT: REVISE
