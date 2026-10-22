1. **HIGH — The stratified Agresti–Caffo interval fails at the boundary (lines 33–39).** If every task has true \(p_A=0,\ p_B=1\), the observed counts are deterministically A=0/16 and B=16/16. The specified method gives Δ=0.888889 and interval **[0.814064, 0.963714]**, excluding the true Δ=1 on every run. Per-task shrinkage accumulates while the standard error decreases.

   **Fix:** report the raw estimate \(D=\frac14\sum_t(x_{Bt}/16-x_{At}/16)\). Replace the proposed extension with the fixed-weight, Wilson-based **additive-CI MOVER** construction in [Tang §2.2](https://arxiv.org/html/2110.12636), explicitly specifying Wilson-width variance recovery and boundary handling. Freeze its equations; qualify boundary, arm-swap and heterogeneous-rate cases, including coverage checks. Arithmetic, `math.sqrt` and `statistics.NormalDist` suffice without SciPy. Recompute the power claim under declared task-specific probability vectors using the selected procedure.

2. **The restructure’s probability justification is unsupported (lines 64–65).** Forty-three endpoints alone cannot establish that a lower B count is “very likely”: endpoints are dependent, and equal deterministic rates produce ties throughout.

   **Fix:** replace that sentence with: “Admission requires nondecreasing observed counts on every frozen endpoint; its pass probability depends on endpoint rates and dependence. Δ summarizes the separately specified completion estimand.” Quantify any stronger probability claim under an explicit joint model.

VERDICT: REVISE
