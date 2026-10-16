**HIGH: none. MEDIUM: none. LOW: none.**

- **Output format:** `complete()` adds `merge_refused` only for a nonempty refusal; `main()` uses the exact JSON spacing expected by the scanner. Plain and escaped forms passed across the registered Codex and Claude carrier shapes.
- **Benign sources:** 300 source/doc/fixture inspection cases produced no matches. Normal receipt writes never persist `merge_refused`.
- **Evidence failures:** Missing, unreadable, or changed files raise even after an earlier refusal. Runner integration converts these failures to STOP; refusals preserve INCONCLUSIVE.
- **Regressions:** No stale callers remain after removing the `sealed` argument. Focused tests passed: 12 tests plus 12 subtests, alongside in-memory carrier, envelope, integrity, and decision probes.

The polling tests cover intact refusal patterns appearing in later chunks; they do not establish reconstruction when the pattern itself is split. No plausible native counterexample was found within this review’s scope.

No files changed. Full filesystem-backed suites were not run under the read-only restriction.

VERDICT: SHIP
