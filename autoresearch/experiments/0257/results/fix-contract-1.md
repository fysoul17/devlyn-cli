# Fix contract 1: 0257 apparatus (code review round 1)

Same hard limits as `results/build-contract.md` (work only in `autoresearch/experiments/0257/` outside `DESIGN.md` and
the review records in `results/`; no commit, push or `git add`; offline tests; no credentials). DESIGN.md wins on any
conflict. Reviews: `results/code-r1-astra.md`, `results/code-r1-grok.md`. Fix every item, each with a test that fails
before the fix and passes after it (state which tests those are).

1. **Zero B successes (CRITICAL).** `decide.py` `at_most` divides by `mine['S']`; with B at 0 successes and A above 0 the
   panel raises instead of reading NO_CLAIM. Skip per-success cost comparisons that are undefined when B has zero
   successes, keep every other clause, and select the headline in DESIGN order. Test: a finished panel with all B
   incomplete and one A complete → `NO_CLAIM` and a token, for development and for easy.
2. **Regrade bypasses the harm latch (HIGH).** `driver.py` returns right after `regrade()`. Reread the regraded verdict,
   apply the harm and identity latch rules to it, and check the latches before advancing. Test: an assessor STOP with
   identity MATCH regraded into a verdict with a scope violation latches and dispatches nothing further.
3. **Deadline lost on restart (HIGH).** Persist the first SMOKE dispatch time at the launch boundary (before the cell
   runs). On start, reconcile with the earliest preserved SMOKE `run/started.json`; never move the timestamp later.
   Test: interruption after a SMOKE verdict exists but before status was written → the deadline is recovered from
   `started.json`; a later restart cannot advance it.
4. **SMOKE A not checked against the sealed forms (HIGH).** After sealing the forms, run `check` on all four SMOKE cells
   and refuse (non-zero exit, clear message) on any violation; the driver must not dispatch `cells.tsv` until that
   qualification record exists and passed. Test: a SMOKE A transcript carrying the sealed Claude form fails
   qualification.
5. **Clearing a latch recreates it (MEDIUM).** `--clear-latch <amendment>` records the amendment path and the sha256 of
   the latched verdict; on restart only that unchanged verdict is exempt. Test: latch → clear → restart continues past
   that cell; a changed verdict file latches again.
6. **NOT_FINISHED suppresses known clauses (MEDIUM).** Keep audited safety observations (false completion, scope, harm)
   from every slot that has them, STOP slots included, independent of statistical eligibility; on NOT_FINISHED still
   list descriptive cost clauses computable from finished slots, while emitting no Fisher p-value and no D. Test via
   `load()` (not by bypassing it): a prefix with a B false completion lists PACKAGE_UNSAFE; a STOP slot's audited false
   completion is listed.
7. **A's safety counts (MEDIUM).** Each panel result reports per task the A and B counts of false completion, scope
   violation and user-data harm; PACKAGE_UNSAFE still depends on B only.
8. **I0185 skills check (MEDIUM).** `prepare.py` must require both registered skills (`devlyn-ideate`,
   `devlyn-engines`) in every installation root the engine's install writes. Make the fake installer write both, and
   test that a bundle missing `devlyn-engines` fails.
9. **Probe timeout (MEDIUM).** `f-malformed-json.js` enforces an absolute 5 s deadline for the request (not an inactivity
   timer) and bounds server cleanup; `judge.py probe` catches a runner timeout, removes the named container, records
   `unassessable` with the error, and continues to the next cell. Tests: a hanging server → `unassessable`, the run
   continues.
10. **Preservation failure erases the POST class (MEDIUM).** Classify the POST independently; when the store check
    cannot run, `store_preserved` is `null` and the POST class stays. Test: JSON-error-400 POST with a failing GET →
    `json_error_400`, `store_preserved: null`.
11. **Unscored probes reported (LOW).** When prediction 6 is unscored, `decision.json` lists every claude F10/F11 cell
    whose probe is missing or `unassessable`, with class and error.

Done means: both test suites pass offline (report exact output); py_compile and `node --check` clean; README updated if
a file's role changed; your final message lists each item with its test name and anything you could not do.
