The statistical revision is acceptable for the explicitly scenario-limited sign reading; Clopper–Pearson is unnecessary for that narrower claim. Independent simulation reproduced powers ≈0.842, 0.663 and 0.330. All power cases now specify eight rates.

One operational defect remains:

- **MEDIUM — quota STOP masks identity failure (Production ready).** [run_cell.py:237](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0256/run_cell.py:237) selects quota before identity failure; [driver.py:235](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0256/driver.py:235) then archives and retries without checking identity. Executing those source branches with in-memory mocks for `CLEAN + quota + MISMATCH` produced two archive operations and another dispatch. R4’s non-STOP latch never evaluates this verdict. **Fix:** before quota archive/retry, persistently latch `MISMATCH` or `UNVERIFIED`; permit `UNKNOWN` only when evidence establishes no owner execution. Qualify combined quota/identity failures across restart. Keep missing-`scope_violations` latching restricted to graded verdicts.

Two wording corrections:

- Line 35: replace “Its 95% interval” with “Its Wilson–MOVER sign interval, using z = 1.96.”
- Line 173: use “quota faults redispatched, assessor faults regraded from preserved evidence, other STOPs held,” matching the retained driver.

The archive-inclusive harm audit and remaining graded-verdict latch changes are acceptable.

VERDICT: REVISE
