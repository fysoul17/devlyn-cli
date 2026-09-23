# 0218 — usage-meter smoke cell: COMPLETE

2026-09-23. One excluded D1 B diagnostic (`0218-smoke`, source `c1c41b8`),
sealed before launch (account/organization equal to prior cells; five-hour usage
26%). Only prompt delta from 0217: the meter sentence ([DESIGN](DESIGN.md)).

| Cell | Result | Owner + review INPUT / OUTPUT | Generations | Reviews |
| --- | --- | --- | --- | --- |
| D1 B smoke | COMPLETE, 230.2s owner | 270,662 / 8,746 terminal (native 243,338 + review 27,324) | 11 | 1 |

Requirement checks 4/4, public suite 0 failed, format gate and scope passed;
combined checks took 15.3s. Blinded assessment complete:true, low/info notes
only (31,673 input, one call).

Prediction held: the owner ran the meter at g1 (0: its first call was still in
flight), g5 (68,503, just before launching review at g6) and g9 (189,712), then
finished below 400,000. This is smoke feasibility only, not reliability, a lower
breach probability or a savings figure; it is not pooled with 0214–0217 or the
screen. Evidence: `.devlyn/0218-run/` in the retained base checkout.
