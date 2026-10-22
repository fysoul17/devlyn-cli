I'll review draft r4 against the round-5 findings and the prior design, read-only, and only confirm or list remaining defects.The three claimed fixes are in the draft. I’ll check them against the r3 text, the interval math, and the 0256 verdict fields.Clopper–Pearson rejection is acceptable. On the codex vector (three tied tasks, one 0/16 vs 16/16), additive 99.375% bounds are about lo −0.13 and hi 0.48, so the sign never reads B_BETTER. Wilson does (lo about 0.14). Astra’s 0.01-vs-0.99 case still has the correct sign (upper limit about 0.975). This reading uses the sign only.

The harm latch matches Grok: non-STOP verdicts only; missing or non-empty `scope_violations`; `teardown` other than `CLEAN`; `identity.status` other than `MATCH`; the post-run audit includes archived attempts. All ten power rows name eight rates. The old 0.55 row is A `(.625, .625, .5, .5)` vs B `(.375, .375, .5, .5)` at 0.33. Equal arm rates in {0, 1} never trip a sign.

1. Line 35 still says “Its 95% interval” while lines 42–44 deny 95% coverage. Delete “95%”.
2. Line 173 “others held” misstates 0256 dispatch (`driver.py`): quota STOPs are archived and retried, assessor STOPs are regraded, and every other STOP stops the run. A hold resumes. Replace that parenthesis with this split.

VERDICT: REVISE
