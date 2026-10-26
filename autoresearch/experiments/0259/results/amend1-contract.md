# Build contract: 0259 amendment 1

Work in `/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0259-amend1` only. Read
`autoresearch/experiments/0259/amendment-1.md` first; it is the specification. Also read
`autoresearch/experiments/0233/quota.py`, the `load` helper and the verdict and stop code in
`autoresearch/experiments/0259/run_cell.py`, `autoresearch/experiments/0259/driver.py` (the archive path for
`shared account fault during execution:`), and `autoresearch/experiments/0259/test_apparatus.py`.

Hard limits:
- Never open, read, copy or print anything under `~/.local/share/nx01/*/auth`, any cell `home/` directory, keychain
  output or credential files.
- Do not touch `~/.local/share/nx01/0259-live` at all. A run is live there.
- Do not touch `/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0259-measured`.
- Do not edit 0233 or any experiment other than 0259. Do not commit or push.

Do:

1. **Add `autoresearch/experiments/0259/quota.py`.** `run_cell.py`'s `load('quota')` already prefers a local file.
   - Keep 0233's behavior and output shape exactly.
   - Add the amendment's one shape: within one stream file, a `result` event with `is_error: true` and
     `terminal_reason: "api_error"` whose most recent preceding `system`/`api_retry` event has `error_status` 401 or
     403 is `('auth', 'claude authentication retry')`.
   - A result that 0233's rule already classifies keeps 0233's kind, so the two rules never double-count.
   - Read native fields only, never prose. Prefer reusing 0233's module (load it by path) over copying it, unless that
     makes the code worse.
2. **Add `autoresearch/experiments/0259/reclassify.py <runtime.json> <cells.tsv>`.** For each measured cell in the
   schedule whose final `verdict-<name>.json` exists:
   - Skip it, unchanged, if its `status` is `STOP` or its recorded `quota.execution` is non-empty.
   - Otherwise compute `quota.classify(<output>/<name>)` with 0259's `quota.py`. If `execution` is non-empty, rewrite
     the verdict atomically. The rewrite sets `status: STOP` and `reason:
     'shared account fault during execution: ' + ', '.join(sorted(kinds))`, matching `run_cell.py`'s wording, and
     sets `quota` to the new classification.
   - Keep every other original field. Add `reclassified: {from_status, from_reason (or null), from_sha256,
     amendment: 'amendment-1.md'}`.
   - Print one JSON line per reclassified cell and a final summary line with the counts checked, skipped and
     reclassified.
   - Fail loudly, with a nonzero exit and no partial writes, on a malformed verdict or a missing cell directory.
   - It must not archive or rename anything. The driver's existing path does that on relaunch.
3. **Update `autoresearch/experiments/0259/README.md`.** Add rows for `quota.py`, `reclassify.py` and `amendment-1.md`.
   Add the operator steps from the amendment. Keep it terse, in the existing style.
4. **Add tests in `test_apparatus.py`:**
   - the d007 shape is detected: ten `api_retry` events, the last with 401 and `authentication_failed`, then the
     error result with `api_error_status: null`;
   - a 401 retry followed by a successful result is not detected;
   - a 403 retry before an `api_error` result is detected;
   - an `api_error` result whose last retry has a non-auth status (for example 529) is not detected;
   - 0233's existing 401 result is still detected exactly once, with 0233's kind;
   - `reclassify.py` rewrites only the matching non-STOP verdict, leaves the others byte-identical, records the
     `reclassified` fields and the reason string, and refuses a malformed verdict without writing.

Done means:
- `python3 -m pytest -q -p no:cacheprovider autoresearch/experiments/0259` passes; report the exact output.
- 0258's suite, run alone, still passes.
- `py_compile` is clean.
- Report the full diff.
