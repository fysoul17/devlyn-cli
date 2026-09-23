# 0215 — color detour removed; B still stopped at the input target

2026-09-23. User: “진행”. Root direct, no resolve. One diagnostic D1 B cell
`0215-pilot-20260923`, source `87ce914`, per [DESIGN](DESIGN.md). Only delta from
0214 B: both declared checks prefixed `env -u NO_COLOR` ([prepare.py](prepare.py));
prompt diff is exactly those two lines, protected files equal. Control mount
equals 0214's except `.pyc` caches; account/organization equal 0213/0214
(five-hour usage 10%); 7 accounting and 5 packet tests passed.

| Cell | Result | Owner + review INPUT / OUTPUT | Generations | Reviews |
| --- | --- | --- | --- | --- |
| D1 B | BUDGET_EXCEEDED at 261.6s; terminal usage UNKNOWN | 422,428 / 10,038 last observed (native 392,873 + review 29,555) | 17 | 2 (second unfinished) |

**Mechanism prediction held.** Zero color-diagnosis generations: every owner
full-suite run passed (1,418 passed, 0 failed) on the first try.

**Sufficiency prediction refuted.** The first Fable review (64.1s) accepted the
fix but flagged two test lines as likely failing Prettier (81 columns; wide
characters). The owner tried Prettier, but it is not installed in the container
(exit 127); it measured widths by hand (g12–14), reformatted the test (g15) and, as required after a source change, launched a fresh review (g16–17).
The input target was crossed during that second review. The same formatter repair
happened in 0213 B. No check ran after the stop; no assessment was started.

Next avoidable block, not acted on: formatting is not among the declared checks,
so it surfaces only in review and forces a second review. Any follow-up is a
separate design decision; do not rerun this cell to chase a pass.

Evidence: `.devlyn/0215-run/` in the retained base checkout, archived as
`.devlyn/0215-run-evidence.tar.gz`. Credentials stayed in owned 0600 scratch.
