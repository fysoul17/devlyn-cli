The three fixes match the contract and DESIGN.md. No new defect.

1. **Refused SMOKE start.** `driver.py:357-362` drops `first_smoke_dispatch` and `registered_caps` when `cell.run` returns 3 and no `smoke-*/run/started.json` exists, then `event` persists that state before `reconcile_smoke_starts` (`driver.py:170-187`). Return 3 is only the image, disk, or preflight refusal (`run_cell.py:204-211`), which is before `started.json` (`0237/cell-init-v1.py:60-61`). A later real start writes its own stamp (`driver.py:349-353`). A kill after `started.json` still recovers through reconcile. That is the first SMOKE dispatch in DESIGN.md:166-169, with no extension.

2. **Probe batch.** `judge.py:90-129` stores the cell result, then calls `TemporaryDirectory.cleanup`. An `OSError` is recorded on that cell and the loop continues to the next cell and to `probes.json`.

3. **Truncated response.** `f-malformed-json.js:28-50` settles once. Response `error`, `aborted`, and `close` reject. The 5s timer rejects before `req.destroy()`. The follow-up failure is caught at `f-malformed-json.js:101-102`, so the POST class stays `json_error_400` and `store_preserved` is null (DESIGN.md:140-143). A normal body still resolves on `end` before `close`.

VERDICT: SHIP
