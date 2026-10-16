The cost rule matches 0232 §6. One HOLD sentence still mis-routes a zero-success result.

Success is rp-d1’s four conditions, report included. Cost is owner wall, input, and output over every dispatched attempt, divided by that count S. Smoke stays outside the gate. UNKNOWN usage stays a STOP and overrides every branch. The 30% incumbent wall cut is not in this gate: §6 limits it to incumbent replacement, and X is the paired control.

- S_Y = 0 fails the cost gate. With S_X = 0 and the other adoption conditions holding, the result is HOLD. The round-3 case (cleanup 3/4 vs 0/4, successes 0 and 0, totals 99 vs 100) does not ADOPT.
- S_X = 0 < S_Y passes by dominance, reported as such, with no raw-sum comparison. S_Y > S_X also meets the tie rule, so a higher raw total still adopts when the quality gates hold.
- Otherwise both counts are positive, and wall, input, and output per success must each be ≤. A higher S does not carry a higher per-success cost. The three metrics do not offset.
- Equal successes with all three costs tied fail the tie bullet and HOLD. A higher S with tied costs still adopts. That is §6’s tie paragraph.

“or an undelivered fact” is gone. Deferred, skipped, and scratch-incomplete clauses match `CLEANUP_PENDING` only. `github.py:359` still sets cleanup to `COMPLETE` or `CLEANUP_PENDING`.

## MEDIUM

**HOLD treats S_Y = 0 as a reconciliation follow-up.** The branch predicate is right: HOLD when every ADOPT condition except cost or strict improvement holds. That is where S_Y = 0 and S_X = 0 land. The next sentence says S_Y = 0 lands there and that reconciliation is the next candidate (`DESIGN.md` lines 213–216).

S_Y = 0 reaches HOLD only when those other conditions hold. If S_X > 0, Y’s successes ≥ X’s fails, and the ordered result is MIXED. A control with one full success and a candidate with none is a success regression, and the gloss pulls it into HOLD. Inside a true HOLD, S_Y = 0 means no Y slot met all four conditions after every delivery passed. Cleanup can be SUPPORTED on 3/4 while verification or merge is the category that is not SUPPORTED. That category need not be FALSE. Lines 220–221 already keep the reconciliation follow-up conditional.

Remove the “lands here / so reconciliation” sentence. Keep the predicate.

## LOW

**The limits paragraph calls every HOLD noise.** A tie, and an S_Y = 0 hold, are exact §6 outcomes. The four-slot power caveat fits a per-success ≤ miss.

VERDICT: REVISE
