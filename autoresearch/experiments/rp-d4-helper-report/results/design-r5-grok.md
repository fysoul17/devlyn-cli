The cost rule and the decision branches match 0232 §6. No HIGH, MEDIUM, or LOW findings.

Success is rp-d1’s four conditions, report included. Cost is owner wall, input, and output over every dispatched attempt, divided by that count S. UNKNOWN usage is a STOP and overrides every branch. Smoke stays outside the gate. The 30% incumbent wall cut stays out of this gate: §6 limits it to incumbent replacement, and X is the paired control.

- S_Y = 0 fails the cost gate. With S_X = 0 and the other adoption conditions holding, the result is HOLD. The round-3 case (cleanup 3/4 vs 0/4, successes 0 and 0) is HOLD.
- With S_X > 0 and S_Y = 0, Y’s successes ≥ X’s fails, so the ordered result is MIXED.
- S_X = 0 < S_Y passes the cost gate by dominance, reported as such, with no raw-sum comparison. S_Y > S_X meets strict improvement, so a higher raw total still adopts when the quality gates hold.
- With both counts positive, wall, input, and output per success must each be ≤. The three metrics stay separate. A higher S with a higher per-success cost is HOLD.
- Equal successes with all three per-success costs tied fail strict improvement and HOLD. The round-4 tie (S_X = S_Y = 1, identical totals, cleanup 3/4 vs 1/4) is HOLD. A higher S with tied per-success costs still adopts.
- HOLD is every ADOPT condition except cost or strict improvement. The predicate names no reconciliation follow-up. The reconciliation sentence stays conditional on reports that still fail reconciliation.
- A HOLD from a tie, and a HOLD from S_Y = 0, are exact §6 outcomes. A HOLD from a per-success ≤ miss is the noise-limited case.

“or an undelivered fact” is absent. Deferred, skipped, and scratch-incomplete clauses match `CLEANUP_PENDING`. `github.py:359` still sets cleanup to `COMPLETE` or `CLEANUP_PENDING`.

VERDICT: SHIP
