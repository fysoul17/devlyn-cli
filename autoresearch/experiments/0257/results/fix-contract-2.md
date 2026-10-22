# Fix contract 2: 0257 apparatus (code review round 2)

Same hard limits as `results/build-contract.md`. Reviews: `results/code-r2-astra.md`, `results/code-r2-grok.md`.
Each item needs a regression test that fails before the fix.

1. **A refused SMOKE start begins the deadline (HIGH).** `driver.py` writes `first_smoke_dispatch` (and
   `registered_caps`) before `cell.run`; when `run` returns 3 (not dispatched: image, disk or preflight refusal) and no
   `smoke-*/run/started.json` exists, delete those keys and persist, so the 21 days start at the first real dispatch.
   Keep the pre-run write so a kill inside `run` is still recovered from `started.json`. Tests: `run` returns 3 → keys
   absent; a later successful start records its own time; a kill after `started.json` exists still recovers it.
2. **Probe batch dropped on cleanup failure (MEDIUM).** In `judge.py probe`, store the cell's result, then leave the
   per-cell `TemporaryDirectory` before continuing; catch `OSError` from directory cleanup (record it on that cell's
   result) and continue with the next cell. Test: `docker rm -f` failing and `rmtree` raising on one cell → later cells
   are still probed.
3. **Truncated responses leave the probe pending (MEDIUM).** `f-malformed-json.js`: handle response `error`/`aborted`
   and premature `close`; the absolute deadline must reject the promise explicitly before destroying the request, with
   settlement guarded so it happens once. Test: GET 200 → POST 400 JSON error → truncated follow-up GET completes within
   the deadline with `class: json_error_400`, `store_preserved: null`.

Done means: both suites pass offline (exact output), py_compile and `node --check` clean, final message lists each item
with its test name.
