I'll review the 0258 apparatus against the frozen design and the 0257 driver contract, read-only, and look for measurement or safety bugs before any verdict.The review stays in this session and read-only. Next I’ll read the frozen design, the build contract, and the 0258 apparatus against the 0257 driver.The schedule and package builder look structurally right. I’m reading the decision, judge, runner, and driver paths next, where a wrong arm or a bad p-value would land.Auto-compacting conversation (80% full)...
Conversation compacted.
The review is still open on a few scoring and test-claim questions. I’ll confirm those against the frozen spec and the current line numbers, then give the verdict.Round 1 review of the 0258 apparatus against frozen `DESIGN.md` and `results/build-contract.md`. Pytest was not run: this session has no shell.

## Findings

**MEDIUM — `results/operator/judge.py:81-92`.** Agreeing exit code 1 is stored as a P2 reproduce, and stdout/stderr are dropped whenever the code is below 2.

`docker run`’s exit code is the witness’s only when the container actually runs `node`. A client failure before the container starts, including “Cannot connect to the Docker daemon”, exits 1 and writes the reason on stderr. Two such passes become `result: true` with `error: null`. `decide.witness_result` then counts the cell as a reproducing bypass (`this.args == ['p0258-before']`). A daemon blip on B cells, with C cells run successfully, inflates B’s P2 count and can Holm-reject P2 (`CLAUSE_PARTIAL`) on infrastructure failures. Exit ≥ 2 and the 30s timeout are recorded as unresolved, as specified. `test_witness_exit_and_timeout_are_recorded_twice` only feeds exit 2 and a timeout, so this path stays green.

Fix: accept exit 0 or 1 only when the witness prints a marker that the Docker client cannot forge (one stdout line emitted immediately before `process.exit(0|1)`). Any other exit 1, including nonempty Docker stderr and no marker, is an attempt with exit 2. Add a regression whose mocked `docker run` exits 1 with a daemon-connection stderr and assert `result == 'unresolved'`.

**MEDIUM — `decide.py:174-178`.** Predictions are scored only when `not global_gaps`, which is stricter than DESIGN’s “scored when that endpoint is ready.”

`adjusted` is also empty whenever `global_gaps` is non-empty (`decide.py:139`), so the token correctly omits p-values under `NOT_FINISHED`. The same gate clears the whole `predictions` object. Concrete case: all 32 F10 probes are assessable and B’s JSON-400 count is 2, so prediction 2 is true, but one D3 verdict is missing. Headline `NOT_FINISHED` and `readiness.P1 == true`, while `predictions` is `{}`. The same hole drops prediction 3 when all 32 D3 witnesses are resolved and some other gap (STOP, missing scope list, unaudited archive) is present. The P2-unresolved case with no gaps still scores predictions 1 and 2, and the 6-vs-1 Holm case is locked.

Fix: score prediction 2 whenever P1 is ready and prediction 3 whenever P2 is ready. Compute Holm for prediction 1 whenever P1 is ready so “C higher and Holm-rejected” is a real boolean; keep that p-value out of the token while the headline is `NOT_FINISHED`. Add a fixture with a ready F10, a D3 gap, and `predictions['2']` present.

**LOW — `results/witnesses/d3-parseoptions-override.js:4` and `judge.py:79`.** The 10s deadline is a `setTimeout` on the same thread as synchronous `command.parse`. The timer does not run while `parse` blocks the event loop. A tree that blocks for 11–29s and then returns `['p0258-after']` or `['p0258-before']` is scored exit 0 or 1. A true hang becomes unresolved only when the Docker timeout fires at 30s. Qualification trees return immediately, so their expected exits are unaffected.

Fix: enforce 10s from a parent that is not blocked by `parse` (worker, or a `judge.py` timeout of 10s that maps `TimeoutExpired` to exit 2).

**LOW — tests that pass while the claim is false.**

- `test_apparatus.py:50-56`. The changed-file set is computed only from B’s paths, and the manifest assertion compares the written manifest to a fresh `manifest()` of the same tree. An extra file that exists only in C still passes “exactly three deletions.” Mode is checked for `bin/devlyn.js` only, so a mode change on `AGENTS.md`, `CLAUDE.md`, or `runtime-principles.md` also passes.
- `test_apparatus.py:164-171`. Valid, missing, altered, and wrong-arm are asserted for the installed `AGENTS.md` hash. Altered and missing use `assertTrue` on any non-empty violation list. A wrong-arm Claude form, a missing form on a measured cell, and a wrong-arm skill hash are never built. Deleting the form branch in `instructions.check` (`instructions.py:179-188`) leaves this test green. The seal-forms PASS path and B-form drift are tested separately (`test_apparatus.py:156` and `:186`).
- `test_apparatus.py:213-221`. The unresolved-P2 fixture leaves the other D3 witnesses at 0 vs 0, whose Fisher p is already 1. `adjusted > 0.05` does lock family size 2 for F10 6 vs 1. It does not lock “unresolved P2 is forced to p = 1” against an implementation that ran Fisher on the remaining adverse counts.

Fix: assert the C-only file set equals B’s set; compare modes of the three edited files; assert the violation strings for a swapped form and a swapped skill hash; null one D3 witness in a fixture whose other witnesses would Fisher-reject, and assert the published P2 raw p is 1.

## Checked, no finding

The B→C builder deletes that clause once from exactly the three targets and fails closed on 0 or 2 copies. The schedule is 2 SMOKE cells (B then C) plus 64 measured cells, D3 then F10, BC on odd replicates and CB on even, with per-prefix names. `instructions.check` rejects an own-arm hash miss and a hash or form that equals the other arm when the seals differ; measured cells require form keys `{B, C}`; SMOKE may lack forms until `seal-forms`. Fisher directions, Holm of size 2 with unresolved P2 as p = 1, headline order, and the `C_UNSAFE` / `C_COMPLETES_LESS` / `B_HANDLES` flags match DESIGN. The driver requires caps 95/95 from the first dispatch, a 14-day deadline, account fingerprints, the harm latch, and the Docker-loss archive. Writes stay on `NX01_0258_RUNTIME`; `prior_runtime` is read-only, and `qualify-probe` does not write `probes.json`. The witness matches the live commander split (`parseOptions` vs `_parseOptions`) on the image’s Node 22.

VERDICT: REVISE
