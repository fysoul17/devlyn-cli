# 0214 — wait diagnostic pilot: A complete, B stopped at the input target

2026-09-23. User instruction: run the prepared pilot (“0214 실험 실행”). Root direct,
no resolve. Pilot `0214-pilot-20260923`, source `426a85d`, exposed D1 material only;
excluded from the0213 cohort, confirmation and advancement. No C cell, no retry.

Launch preparation followed [PREPARATION](PREPARATION.md). The rebuilt control
mount matches0213's seal byte-for-byte except17 `.pyc` caches (new embedded
mtimes; D1 is Node and does not import click). Calibration reproduced0213's
summary digest `253aed40…`; 7 accounting and5 packet tests passed. Current-login
Fable account/organization fingerprints equal0213's; five-hour usage was3%.
Assessment used the same pinned host Claude2.1.278. Both prompts equal the0213
prompts plus only the [waiting instruction](common-wait.txt); protected files match.

| Cell | Result | Owner + participant review INPUT / OUTPUT | Generations |
| --- | --- | --- | --- |
| D1 A | COMPLETE, 202.8s owner | 399,291 / 6,912 terminal (native 370,695 + review 28,596) | 16 |
| D1 B | BUDGET_EXCEEDED at 242.1s; terminal usage UNKNOWN | 411,149 / 8,208 last observed (native 389,900 + review 21,249) | 16 |

A passed four frozen requirement checks and the public suite (1,418 passed,
1 skipped, 0 failed). Its blinded assessment returned complete:true with only an
environmental note and a low out-of-scope edge case (29,771 / 4,296, 1 call).
B exceeded 400,000 by 11,149 after one Fable review; its container was removed
and no B assessment was started. Raw classes: BUDGET_EXCEEDED, UNKNOWN, INFRA_INVALID.

**Prediction not refuted.** Neither owner issued a shorter sole-call review wait.
Each cell polled its running review twice at 30000ms: one empty 30.0s wait, then
the result (A 0.0s, B 0.38s). B's other sole poll (isolated full test run, 30000ms)
returned output after 6.75s. Empty review polls fell from two to one per cell.

**Input did not fall.** B's native input (389,900) matches0213 B (390,690), with the
same 16 generations; B's other generations included an isolated full-suite rerun
and a post-review Unicode boundary probe. B's generation inputs were 12k–31k each,
so the observed total tracks generation count more than waiting. A rose from0213's 370,000 to 399,291.
One pair per arm, no counterfactual: no causal, efficiency or adoption claim.
The instruction does not keep B below the registered target; do not raise the
target, weaken checks or rerun this pilot to chase a pass.

Evidence: `.devlyn/0214-pilot/` in the retained base checkout (launch seal, auth
fingerprints, calibration, both cells, `pilot-stop.json`), archived as
`.devlyn/0214-pilot-evidence.tar.gz`. Credentials stayed in owned0600 scratch.
