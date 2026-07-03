# Staging — written and self-validated, NOT yet measured

Fixtures here are invisible to `lint-fixtures.sh` and
`pair-candidate-frontier.py` (both enumerate top-level `fixtures/F*` only).
A fixture may not enter the active set unmeasured — the packaged audit
fails on `candidate_unmeasured` by design.

Activation contract (same session, in this order):
1. `mv fixtures/staging/<FID> fixtures/`
2. `bash scripts/lint-fixtures.sh`
3. bare + solo arms via `run-full-pipeline-pair-candidate.sh`, then
   `headroom-gate.py` (bare ≤ 60, solo ≤ 80, both clean)
4. FAIL → move to `fixtures/retired/` with RETIRED.md or the rejected
   registry — never tune the oracle to pass.
