# Fix contract r1: 0258 apparatus

Same hard limits as `build-contract.md`. Fix every finding in `results/code-r1-astra.md` and `results/code-r1-grok.md`,
with a regression test for each, and nothing else:

1. `decide.py`: every preserved attempt (archived `verdict-*.stop-*.json` included) must carry an explicit
   `scope_violations` list or an explicit root scope judgment in the audit file (`scope_archived` mapping name → list);
   otherwise a gap. An archived C attempt with a scope violation lists `C_UNSAFE`.
2. Witness timeout: enforce 10 s from `judge.py` (container/subprocess timeout 10 s for this witness, timeout → exit 2,
   unresolved), not only the in-process timer.
3. Witness exits: the witness prints one marker line on stdout immediately before exit 0 or 1
   (`P0258-WITNESS public` / `P0258-WITNESS bypass`); `judge.py` accepts exit 0/1 only with the matching marker and
   records anything else (Docker client errors, exit 1 without marker, stderr from the client) as exit 2 with the
   output kept. Regression: mocked `docker run` exits 1 with a daemon-connection stderr → unresolved.
4. `judge.py probe`: a non-object or malformed last JSON line is `unassessable` and takes the registered single rerun.
5. `instructions.py`: reject duplicate attachment paths; tests build real attachment shapes for missing, altered,
   wrong-arm (swapped form) and duplicate cases, plus a swapped skill hash, asserting the violation strings.
6. Readiness per DESIGN: a missing F10 verdict makes P1 not ready; a missing D3 verdict makes P2 not ready; only an
   unresolved STOP or instruction assertion, a missing mandatory judgment or an unaudited attempt makes the whole run
   NOT_FINISHED. Predictions: 1 and 2 scored whenever P1 is ready (prediction 1 uses the fixed-size Holm with P2 at
   p = 1 when P2 is not ready), 3 whenever P2 is ready, even under NOT_FINISHED; p-values stay out of the token under
   NOT_FINISHED. Tests: ready F10 with a D3 gap scores prediction 2; an unresolved D3 witness in a fixture whose other
   witnesses would Fisher-reject publishes P2 raw p = 1.
7. `test_apparatus.py` package test: C's file set equals B's; modes of the three edited files equal B's.

Done means: both test suites pass offline (report output); `py_compile` clean; the witness rerun on the four 0257
trees with plain `node` still gives 1,1 / 1,1 / 0,0 / 0,0 and prints the markers. Report what you changed and ran.
