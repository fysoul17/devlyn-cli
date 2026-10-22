I'll review the round-4 draft against the round-3 findings and the Δ specification, read-only. First I'm loading the design, the prior draft, and the review notes.The draft and the round-3 findings are in hand. Next I will check the 43- and 11-test counts, the crash rule, and the Agresti–Caffo formula against the 0256 apparatus.The round-3 family, Holm, cost, account, deadline, and prediction fixes match the apparatus. Two rules are still wrong, and the reason given for promoting Δ overclaims.

1. **The stratified Agresti–Caffo interval does not cover the written Δ** (lines 33–39, 57–58). Adding one success and one failure centers the interval on (16/18)Δ. Four tasks at 0/16 vs 16/16 give center 8/9 and interval about [0.814, 0.964], which excludes the true Δ = 1 on every run. The “about 80%” line is a different Wald calculation and names no task-rate vector.

**Fix:** Keep the raw estimand D = ¼ Σ_t (s_B,t − s_A,t)/16. Use an equal-weight MOVER interval from Wilson limits, z = 1.96 exactly (`math.sqrt` only). Per arm, den = 16 + z², mid = (s + z²/2)/den, half = z √(s(16−s)/16 + z²/4) / den, (l, u) = mid ± half, p = s/16. Then lo = D − √[(1/16) Σ_t ((p_B−l_B)² + (u_A−p_A)²)] and hi = D + √[(1/16) Σ_t ((u_B−p_B)² + (p_A−l_A)²)], clipped to [−1, 1]. **B_BETTER** if lo > 0, **B_WORSE** if hi < 0, else **NO_DETECTED_DIFFERENCE**. Predictions 2 and 4 score this D. Qualify four tasks at 0/16 vs 16/16 (D = 1 and the interval contains 1), the arm swap, and one 16-vs-0 task with three 8-vs-8 tasks. Delete the 80% sentence unless power is recomputed for this interval under an explicit four-task alternative.

2. **“A task’s oracle crash fails each of its frozen rows” over-applies** (line 180). In `0222/check.py`, a D3/D4 crash replaces the oracle rows with one synthetic id. Public checks are already scored. On I0185, B5, F10, and F11, a crashed command fails only that row. Failing every frozen row marks passed checks and uncrashed rows as failures and can Holm-reject them.

**Fix:** On a D3/D4 synthetic crash, FAIL D3.1–D3.6, or D4.1-2, D4.3, D4.4, and D4.5. Do not add `D3.oracle` or `D4.oracle`. Leave public checks as recorded. Any other crashed command fails only its own frozen row.

3. **“Very likely lower on at least one of 43 endpoints” is not shown** (lines 64–65). At p = 0.5 an independent 16-vs-16 comparison ties about 14% of the time, and these endpoints are dependent. Promoting Δ is not outcome-shaped: Δ was already the r1 estimand, the §6 clauses are unchanged, and nothing has run.

**Fix:** Replace that sentence with: “A §6 pass requires every frozen count to be no lower; that probability depends on the rates and the dependence. Δ is the completion summary. Holm’s first-step power is the figure above.”

4. **The harm latch has no driver predicate** (lines 142–145). User-data harm is a `decisions.json` judgment. Restarts read `driver-status.json`.

**Fix:** Do not dispatch the next cell until that cell’s harm judgment is present. `true` latches in `driver-status.json`. A missing judgment is not a negative. Store the first SMOKE dispatch time in that file and keep the 21-day rule.

VERDICT: REVISE
