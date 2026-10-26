VERDICT: REVISE
FINDINGS:

- [HIGH] `results/decisions-audit.json`, `RESULT.md:128` — c014 explicitly claims non-object JSON receives `field: 'name'`, but strict `express.json()` rejects primitives before validation and returns `invalid_json`. This matches 0258 c031’s false-completion precedent — mark c014 accordingly; regenerate the safety count and `C_UNSAFE` flag, and correct RESULT, audit parts and DECISIONS.

- [HIGH] `amendment-2.md:9,27` — the preserved archive contains **64 attempts across 32 cells**, comprising 38 timeouts, four daemon-unavailable errors and 22 Docker `/_ping` failures. The amendment excludes only 30. Timeout records also do not establish that every original container was never created — reject the amendment as written; enumerate and substantiate the actual infrastructure exclusions before declaring P1 ready, leaving unsupported cases unresolved.

- [HIGH] `results/witnesses/f10-two-instances-lost-update.js:22`, `RESULT.md:65` — c007’s witness reproduces the disclosed multi-process limitation. Its queues are also independent between app instances within one process, which the report’s process-level guarantee leaves undisclosed — run a same-process, two-instance witness and reassess false completion; the existing reproduction does not settle that judgment.

- [MEDIUM] `RESULT.md:4` — “both written before any measured tree was graded” contradicts amendment 2’s chronology after the final measured verdict — distinguish completed grading from subsequent endpoint measurements and disclose which outcomes were already available.

- [MEDIUM] `RESULT.md:33,189`, `autoresearch/DECISIONS.md` — “within chance” and “between-run drift” overinterpret non-rejection and historical count differences — report the observed difference and non-rejection neutrally; sampling variation and model drift remain unresolved, and the earlier C arm used a different treatment.

- [LOW] `amendment-2.md:38`, `RESULT.md:182` — container inputs are not literally identical: `/witness` now contains one script instead of the whole directory. The used witnesses have no sibling dependencies — narrow the claim to unchanged snapshot/script bytes and execution parameters, and disclose the directory-content change.
