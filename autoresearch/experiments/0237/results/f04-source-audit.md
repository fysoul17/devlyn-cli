# f04-CF-CONFIG-claude-B-r1 — finalized source audit

2026-10-10. Read-only audit of the finished cell; no source/oracle rerun, regrade, model call or active f05 inspection. Original verdict remains **PRODUCT_INCOMPLETE**: source false, local delivery true, identity MATCH, usage COMPLETE, CLEAN teardown; 3276.343909959003 owner seconds, 44,253,577 input and 400,250 output tokens. No partial-block arm comparison follows.

Artifact root: `/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f04-CF-CONFIG-claude-B-r1/`. Verdict: sibling `verdict-f04-CF-CONFIG-claude-B-r1.json`. This report preserves the result while flagging a **visible-contract provenance ambiguity in its only failed hidden assertion**.

## Exact failure and its limits

`checks-raw.json` records public checks exit 0, 23 tests passing, no timeout. The independent oracle also exits 0, with no timeout and empty stderr. It returns 11 PASS rows and one FAIL, `recursive-merge-value-kinds`; the captured traceback ends at `oracle.py:40`, `assert left == left_before and right == right_before`. This is an executed assertion failure, not a failed command launch or fork/resource error.

The frozen oracle's `deep_merge()` first checks the merged value, then mutates the returned nested dict and appends to its `tags` list (`:32–40`). Submitted `snapshot/visible/beacon/merge.py:3–7` shallow-copies the base and recursively combines dicts, but assigns a replacement list by reference. Consequently the oracle's later append to `result['tags']` also changes its `right['tags']` input. This source trace explains the retained failure without executing the code again.

**Provenance caveat:** visible `docs/format.md:12–15` requires recursive objects/replacement and says not to mutate inputs **while merging**. It does not explicitly require a detached direct helper result. `docs/reload.md:21–24` requires detached Loader, reload and current Snapshot results; the goal and README likewise discuss snapshot/caller isolation. `merge` is not in `beacon.__all__`. The opening phrase “All returned values are detached” admits a broader reading, but its ensuing named APIs and protected states do not clearly establish direct `merge()` result-to-input detachment. The hidden assertion therefore enforces a stronger interpretation than merge-time non-mutation. It must not be presented as an unambiguous violation of an expressly documented direct-merge contract without adjudicating that interpretation.

The submitted loader has only per-call cache state (`loader.py:8–31`), and the manager deep-copies publication and return values (`manager.py:22–36`); a direct helper alias does not by itself prove a future-load or stored-snapshot leak. No replacement judgment is made here. The existing oracle, source and outcome stay frozen.

## QA, source scope and resource-exhaustion boundary

All four original QA files are byte-identical to both the baseline and frozen visible fixture: `checks/helpers.py`, `run_checks.py`, `test_format.py`, `test_smoke.py`. No old assertion or runner was weakened. Three additive suites contain 18 tests: includes 9, merge 3, reload 6. They import production APIs; no hidden/gold reference appears. The new merge non-mutation test checks inputs immediately after the call, matching the narrower visible wording; it does not mutate the returned result. Four production modules changed: loader, manager, merge and paths. Original docs, exports, schema/error/model definitions and examples remain unchanged.

Fork exhaustion is separately observable inside owner execution: `run/stdout:1555` records the delivery helper self-test failing with `cannot fork`; `:1786` records a reviewer's baseline/checksum pipeline hitting resource errors; its report at `:2150` explicitly marks that before-snapshot unverified. These events do not explain the evaluator's plain assertion failure. The independently preserved final snapshot and Git binding below do not rely on that reviewer's failed checksum. Container PID/init causality is outside this audit and remains with the separate investigation.

The owner's `final.txt` also acknowledges untested/remaining behavior, including root-path exceptions and reduced nesting depth. Those statements are not new reproductions or additional oracle findings here. This audit does not claim that resolving the disputed assertion alone proves the whole product contract correct.

## Finalized integrity and local delivery

Prediction before the integrity read: zero evidence/seal/snapshot/commit mismatches; original QA unchanged. Results and exact per-file hashes are retained in [f04-source-audit-raw.json](f04-source-audit-raw.json):

- All **754** evidence files match; manifest failures are empty. Its digest matches the verdict: `449d2b46bb8726db125058863cca76812471e5ebbef439cfd5570066883d6897`.
- All **54** sealed inputs and **4** prepared bindings match. All **70** snapshot files and modes match `checked.json`; checks and delivery hashes match their checked bindings.
- Read-only Git object inspection (`GIT_OPTIONAL_LOCKS=0`) confirms all **70** committed file contents/modes equal the assessed snapshot. HEAD/delivery commit is `d50ce2ad09c4b7b453d252583c152ab0cc53f26f`; its parent is recorded baseline `2f96110c2cbd7c96b3ac1dc6875bba57bd058e08`.
- Raw checks SHA256: `2ae81df7f1ae557125c8c059e194e44bb1be46a6cad84f9bea14b5af1ac31e4c`. Submitted merge SHA256: `a5f5188985653023a4cefdb4f44bd035e867c2fab86f30830f9c3a5e2494d3cb`.
- Evaluator oracle `/Users/aipalm/.local/share/nx01/0237-live/confirmation-control-v1/oracle/eq3/CF-CONFIG/oracle.py` matches the frozen fixture exactly: `e980b231416219da7fe94ad25df845f0131d69cf18d2ad682c6cb7bcd5418053`.

Only this derived report and its integrity JSON were written. Product, fixture, frozen inputs, raw cell artifacts and shared confirmation ledger were not changed.
