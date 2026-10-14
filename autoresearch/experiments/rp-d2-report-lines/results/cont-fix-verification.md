# Accounting continuation fix — verified 2026-10-14

Changes are confined to rp-d2-report-lines. No DESIGN.md, 0254, 0255, rp-d1 or
older source edits; no project commit, network, Docker, GitHub, model calls or
real credential reads. Existing offline suites use temporary local Git fixtures.
The no-model constraint precluded another cross-model review.

- `runner.py:74`: Claude admits only the transient gap; Codex's three patterns
  are unchanged.
- `runner.py:90`: recheck the original sealed evidence, reject all non-system
  error rows and assistant API-error notices, then run unchanged 0254 on a
  private copy with only system api_error/api_retry rows removed. No sealed
  evidence or counters are rewritten.
- `runner.py:138`: only the final whole/owner aggregate comparisons can remain
  uncertain. Every non-accounting require precedes them. Require owner-only
  retries and nonnegative owner excess; any whole excess must match. Earlier
  counter/child-aggregate failures STOP, so they cannot conceal lifecycle checks.
- `runner.py:154`: invoke the inherited 0255 account function's unchanged code
  with a private namespace for its accounting dependency, entering its scope
  inventory on the original cell only after structural acceptance. This avoids
  copying the inventory or mutating module globals. The private scope result
  never supplies run tokens/completeness; persisted usage stays UNKNOWN.
- `runner.py:219`: graded reason is `accounting-only UNKNOWN; graded`; the
  inherited STOP remains byte-for-byte in `accounting-stop.json`.
- `test_rpd2_continuation.py:90`: real auditors/inventory exercise retry-only,
  account/session mismatch, child lifecycle/aggregate, body inventory, foreign
  carriers (sealed and unsealed), independent invocation/terminal-body launches,
  scope parser failure, aggregate/counter failures, Codex patterns and smoke.
  The existing lifecycle tests retain their separate mocked eligibility boundary
  and now assert the graded reason (`test_rpd2_runner.py:540`, `:574`).
- `README.md:66`: documents the optional private fixture and narrow continuation.

Verification:

- Targeted final run: **46 passed in 5.24s**, no skips
  (`cont-fix-targeted-r2.log`).
- README offline combined suites: **279 passed, 152 subtests passed in 106.55s**,
  no skips (`cont-fix-offline-suites.log`). Collection confirms **143 rp-d1** and
  **136 rp-d2** tests. The 46 targeted tests are included in the 136.
- Initial targeted run: 35 passed, 1 failed (`cont-fix-targeted.log`). Its test
  used bare `codex exec`; the frozen launch-only detector recognizes the
  `codex-monitored.sh` wrapper instead. The corrected fixture exercises that
  existing contract, plus `claude -p` and the peer helper. No frozen detector
  behavior was changed or claimed fixed.

The real smoke-claude-X case is **ineligible**, including for hypothetical
measured continuation: removing its two system retry/error rows exposes
`orphan or missing body file` — **two unindexed body files**, no missing indexed
files. Its actual smoke phase also independently forbids continuation. See
`cont-fix-real-eligibility.json`. The direct check verified all **81 native
evidence files**, the seal and original verdict before and after; none changed.
Credential files were excluded from reads/copies. A private temporary copy is
tested as a negative regression; synthetic valid receipts isolate retry-only
eligibility and adversarial cases because the real case is not retry-only.
