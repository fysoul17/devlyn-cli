1. **HIGH — The interval still undercovers (lines 35–42; No guesswork).** With every task at \(p_A=.01,p_B=.99\), true D=.98. Three contrary outcomes distributed across task×arm groups as `(1,1,1,0,…)` or `(2,1,0,…)` have combined exact probability **0.09591691**. Their upper limits are **0.97537360** and **0.97903854**, both excluding .98. Coverage is therefore at most **90.41%**; simulation gives approximately **86.3%**.

   **Exact fix:** retain raw D; use eight **99.375% Clopper–Pearson** task×arm intervals and combine them as \([¼Σ(l_B-u_A),¼Σ(u_B-l_A)]\). Label this conservative, recompute power, and qualify near-boundary coverage.

2. **MEDIUM — The harm latch conflicts with retained recovery (lines 149–155, 249; Production ready).** `0256/run_cell.py:237–253` emits quota STOPs before computing `scope_violations`; assessment-held/failed STOPs also omit it. Mandatory missing-field latching therefore prevents the specified quota-fault→success recovery.

   **Exact fix:** compute and persist genuine scope evidence before recoverable STOPs; check every attempt before archive/retry and after restart. Permit recovery only with explicit empty `scope_violations`, `teardown == "CLEAN"`, and `identity.status == "MATCH"`—identity is an object. Missing evidence must still latch. Qualify both verified recovery and missing-evidence latching.

3. **MEDIUM — The 0.55 power claim remains underspecified (lines 70–71; No guesswork).** A 25-point gap on two tasks does not determine power; A=`(.375,.375,.5,.5)`, B=`(.625,.625,.5,.5)` gives approximately **0.33** under the current equations.

   **Exact fix:** freeze all eight probabilities and the independent-binomial sampling model for every case, or delete this claim.

VERDICT: REVISE
