**MEDIUM — ADOPT still allows a tie that §6 rejects.** [DESIGN.md:203](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/DESIGN.md:203) allows equal success counts and equality on all three costs. [0232 §6:153](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/iterations/0232-harness-ladder.md:153) additionally requires more successes or at least one strictly lower per-success cost.

Counterexample: X cleanup 1/4, Y cleanup 3/4; both have verification and merge 4/4, reconciliation supported only in slot 1, and therefore `S_X = S_Y = 1`. With all deliveries and guards passing, no FALSE categories, and identical cost totals, ADOPT fires. §6 explicitly rejects this tie.

Add the strict-improvement condition to ADOPT; failure can fall through to MIXED.

The requested denominator, both zero-success cases, COST HOLD routing, and removal of “or an undelivered fact” are correct. No HIGH or LOW findings.

VERDICT: REVISE
