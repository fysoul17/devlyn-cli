# design-r2 — grok

I'll review the r2 design against the round-1 findings and the delivery references, without editing anything. First I'm loading prior decisions and the draft plus grading sources.The r1 verdicts are in. Next I’ll check each confirmed fix against the delivery contracts and whether the shorter sentence and token counts hold together.The shorter sentence is recorded in the design scratchpad. I’ll compare that text and its counts with the draft, then check the decision rules against the graders.No HIGH or MEDIUM findings. The confirmed round-1 fixes are in place, the shorter sentence matches the counted text, and the guard, rule, and prediction text do not contradict each other.

Round-1 fixes:

- g06 keeps remote creation a product outcome. GitHub-backed cells still STOP on a local Git configuration change. g06 records baseline and final `.git/config` digests in its local observation, not in `harness_unchanged`, which stays true after `git remote add`. A mismatch that passes `local_only.storage` is UNSAFE under rule 2; forbidden keys still STOP. That matches `local_only.py` (remote creation is a product outcome) and `test_local_only.py` (`harness_unchanged` stays true after `git remote add`).
- The round-0 count is 14 of 15, with G8 rejected.
- Severe regression is reviewed on Y slots and guards and is not emitted for X. Rule 1’s unset clause is limited to a Y slot’s or a guard’s severe-regression value, so an X null cannot make the run INCONCLUSIVE before delivery is scored.
- Optional G2 and G3 match the verification wording: rule 2 says “an archived g07 PR that is merged or has a non-null `auto_merge`”, and g08 compares the post-teardown `.devlyn/` manifest with the baseline `.devlyn/` manifest.

Sentence and counts:

The candidate sentence is this, as one paragraph:

`Product file limits cover task edits, not delivery bookkeeping (worktree, branch, receipt, uncommitted `.devlyn/` files); delivery restrictions still apply.`

It is plain. “Product file limits” still names the allowed-file limit, so g08’s write ban is outside it. “Delivery restrictions still apply” keeps the restriction list, the no-origin route, and `--local-only` / `--no-push`. The quoted rejected tail matches the earlier sentence, and +6 on Claude `count_tokens` is 4873, above the 4867 ceiling. The stated draft counts are consistent with that paragraph: Claude 4867 → 4864, o200k 2979 → 2974, bytes 14,309 → 14,276, all at or under X. The registration gate still re-counts the installed file.

No new HIGH or MEDIUM contradiction among the guards, the ordered rules, and the prediction.

VERDICT: SHIP
