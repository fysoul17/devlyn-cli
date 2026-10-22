I'll review the round-5 draft against the round-4 findings and the source equations, read-only, and report only remaining defects.Round-4 findings are loaded. Next I’ll check the r3 equations, crash rule, power claims, and harm latch against the source and the prior draft.The equations match Grok’s text on the page. I’ll check them against Wilson/MOVER, the crash rule in `check.py`, the verdict fields, and the power numbers.The Wilson-MOVER equations, the 0-vs-16 / arm-swap / mixed-rate checks, the D3/D4 crash rule, the 85%/70% caps, and leaving the user-data-harm audit until after the run all match the apparatus. Two defects remain.

1. **The harm latch does not match the verdict.** `identity` is the object from `cell.identity` (`status` is `MATCH`, `MISMATCH`, `UNVERIFIED`, or `UNKNOWN`). `scope_violations` is written only after assessors succeed (`0256/run_cell.py` `grade`). A quota STOP and an assessor STOP omit it, and `driver.py` retries those.

**Fix:** Latch a non-STOP verdict when `scope_violations` is missing or non-empty, `teardown != "CLEAN"`, or `identity["status"] != "MATCH"`. Leave a STOP to the current dispatch rule. Qualification: each bad field on a graded verdict latches across a restart; a quota STOP and an assessor STOP do not.

2. **Two power cases have no probability vector.** For two tasks at 0.625 vs 0.375 and two at 0.5 vs 0.5, the Wald power of this interval is about 0.30 (se ≈ 0.087). About 0.55 is the power when the other two tasks have variance 0. “At boundary rates, never” is false for four tasks at 0/16 vs 16/16, which always reads `B_BETTER` (interval about [0.863, 1]).

**Fix:** Name every simulated vector, including 0256 (claude A 1, 0.5, 0, 1 vs B 0.5, 0, 0, 1; codex A 1, 1, 0, 0 vs B 1, 1, 0, 1). Replace 0.55 with the resimulated frequency. State that when all four tasks have equal arm rates in {0, 1}, neither one-sided reading occurs.

VERDICT: REVISE
