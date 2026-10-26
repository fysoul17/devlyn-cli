VERDICT: SHIP
FINDINGS:
- none

The round-1 HIGH is closed. In `autoresearch/experiments/0259/decide.py` `load`, a present final SMOKE verdict whose name is absent from `decisions['audited']` appends `<name>: final report not audited` before parsing. `decide` already maps any `global_gaps` to `NOT_FINISHED`, ahead of `PRINCIPLE_IMPLICATED`.

Against `autoresearch/experiments/0258/decide.py`, the only logic difference is that two-line gate. The other differences are the registered 0259 renames: the docstring, `PRINCIPLE_IMPLICATED` / `PRINCIPLE_PARTIAL`, and the `0259:claude=` token.

`test_final_smoke_requires_audit_before_rejecting_headline` matches the contract. All 64 cells are audited and ready; C has 8 JSON-400 F10 results and B has 0, so one-sided Fisher p ≈ 0.00122 and Holm ≈ 0.00245, which rejects. With both SMOKE verdicts present and only the second unaudited, `missing` is exactly that gap and the headline is `NOT_FINISHED` while readiness stays true. After that name is appended, the gaps are empty and the headline is `PRINCIPLE_IMPLICATED`. The audited smoke adds no gap. `test_smoke_attempts_are_safety_only` now lists the final smoke in `audited` so its empty-gap assertion matches the new gate; its `C_UNSAFE` counts are unchanged.

I did not re-run pytest. This check is the diff and the test math. Root’s report was 32 passed, 33 subtests, and 0258’s suite 27 passed.
