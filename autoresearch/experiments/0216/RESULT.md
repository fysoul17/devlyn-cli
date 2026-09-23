# 0216 — format gate: B completed under the input target

2026-09-23. User: “진행”. Root direct, no resolve. One diagnostic D1 B cell
`0216-pilot-20260923`, source `299908e`, per [DESIGN](DESIGN.md). Only prompt
delta from 0215 B: the declared format check ([prepare.py](prepare.py)); the
evaluator conjoins the same check ([check_cell.py](check_cell.py)). Control mount
equals 0215's plus integrity-verified Prettier 3.8.3; same account (five-hour
usage 13%); 7 accounting and 5 packet tests passed. Pre-launch controls: the fresh
cell passes the gate; a copy of 0214 A now fails completion on format alone.

| Cell | Result | Owner + review INPUT / OUTPUT | Generations | Reviews |
| --- | --- | --- | --- | --- |
| D1 B | COMPLETE, 266.3s owner | 353,934 / 10,731 terminal (native 309,986 + reviews 43,948) | 13 | 2 |

Four requirement checks, the public suite (1,420 passed, 1 skipped, 0 failed), the
format gate and scope all passed. Blinded assessment: complete:true, one info note
(34,290 / 3,470, 1 call, separate from the owner pool). First D1 B completion
across 0213–0216.

Predictions: **no post-review formatting repair — held**; **COMPLETE with known
terminal input < 400,000 — held**. **Review 1 received a passing format result for
its exact source — not met as written.** At g2 the owner ran
`python3 /control/review.py --help`; [review.py](../0210/review.py) ignores
arguments, so this started a real Fable review (19.4s) of unmodified source with
no checks, consuming one of the two reviews. The substantive review (review 2,
43.8s) received the passing format result for the final source.

Not acted on: `review.py` accepts `--help` as a dispatch, so a probe can spend a
review slot. One cell, no control: feasibility only, not a causal effect, savings
figure or adoption. Historical verdicts are unchanged; prospectively 0214 A would
fail the format gate.

Evidence: `.devlyn/0216-run/` in the retained base checkout, archived as
`.devlyn/0216-run-evidence.tar.gz`. Credentials stayed in owned 0600 scratch.
