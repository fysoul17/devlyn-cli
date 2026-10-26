# Fix contract r2: SMOKE audit readiness

Same hard limits as `results/build-contract.md`.

Code review round 1 ([code-r1-astra.md](code-r1-astra.md), HIGH, inherited from 0258): in `decide.py` `load`, a
final SMOKE verdict that is not in `decisions['audited']` adds no gap, so with all measured cells audited the run can
read `PRINCIPLE_IMPLICATED` while a SMOKE false completion or harm was never judged. DESIGN requires the audit to
cover every attempt.

Do:

- In the SMOKE loop of `decide.py` `load`, a present final SMOKE verdict whose name is not in `decisions['audited']`
  adds the global gap `<name>: final report not audited` (same wording as `judgment_gap`). Nothing else changes.
- Add a regression test: all 64 measured cells audited and ready with a P1 that would reject, both SMOKE verdicts
  present, one SMOKE name missing from `audited` → headline `NOT_FINISHED` and the gap listed; with both audited →
  the rejecting headline.

Done means: `python3 -m pytest -q autoresearch/experiments/0259` passes (report exact output) and `py_compile` is
clean. Report the diff.
