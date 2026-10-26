# Fix contract: 0260 code review round 1

Same hard limits as `results/build-contract.md` (work only in `autoresearch/experiments/0260/`, never commit or
`git add`, no Docker, no network, never edit `DESIGN.md` or the review files in `results/`). Findings:
`results/code-r1-astra.md` and `results/code-r1-grok.md`. Change only `results/operator/judge.py` and
`test_apparatus.py`, plus `quota.py`'s docstring (item 4).

1. **A completed attempt is never lost** (Astra HIGH 1). In both `probe` and `run`, write the results file after every
   completed attempt, not only after a cell's last one. A later call resumes a cell from its stored attempts and runs
   only the missing ones: a probe runs a second attempt only when the stored first one is `unassessable` (as 0259);
   a witness runs only the missing of its two passes. A cell whose attempts are already complete is not run again
   and its stored record is returned unchanged, so repeating a call can never replace a measurement. A stored
   partial witness record (one pass) has `result: 'unresolved'` until its second pass exists, and keeps the 0259
   shape (`attempts`, `result`) otherwise. A failed `docker create` still records nothing for the attempt it was
   making. Each witness record also stores the witness file's sha256 (`witness_sha256`); resuming or returning a
   record made by a different witness file under the same label raises an error that names the cell, so a revised
   witness needs a new file name.
2. **A cleanup failure after a started container does not drop the outcome** (Astra HIGH 2, Grok LOW 1).
   `docker_attempt` raises only for a failed or timed-out `docker create`. For a started container it returns the
   outcome and any cleanup error; the caller records the attempt as it would without the cleanup error, adds the
   cleanup error text to the attempt (key `cleanup_error`, present only when cleanup failed), and persists it. The
   next attempt's `docker create` then meets the leftover container name and stops the call through item 1's rule.
3. **Restore the lost assertions** (both LOW): exits `[2, 1]` give `unresolved`, and Docker's error text is kept on
   exit 2, as 0259's test checked.
4. `quota.py` docstring: "0233 shared account classifier with 0259's retry-only authentication shape." (the shape is
   0259's, not new).

Tests, with a fake `subprocess.run`: (a) a probe whose first attempt is `unassessable` and whose retry's create fails
keeps the first attempt in `probes.json`, and the next call runs only the retry; (b) a witness whose second pass's
create fails keeps pass one (`result: 'unresolved'`), and the next call runs only pass two; (c) a repeated call on a
complete cell runs no Docker command and returns the stored record; (d) a cleanup failure after a completed
`docker start -a` records the real outcome with `cleanup_error` for both probe and witness; (e) the existing create
timeout, create error and start timeout tests still pass.

Done means: `python3 -m pytest -q -p no:cacheprovider autoresearch/experiments/0260` passes (report the output), the
0259 and 0258 suites still pass when run separately, `py_compile` is clean, and your final message lists what changed
and the test output. Do not claim anything you did not run.
