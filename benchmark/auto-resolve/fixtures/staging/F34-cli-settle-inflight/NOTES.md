# F34 CLI settle in-flight

## Failure mode

Detects implementations that couple authorization completion order to
settlement order. The two cheap-but-wrong shapes: (a) sequential
await-per-transfer — correct ledger, fails the visible overlap requirement
(`high_water >= 3`); (b) apply-as-authorizations-resolve — meets overlap,
corrupts file-order settlement (flips `t-60` accept and `t-40` reject in the
verifier input). The correct shape starts authorizations concurrently and
settles strictly in file order afterward — the decoupling is the measured
skill (Tier-1 "H1" from memory `project_pair_fixture_tier1_2026_05_05`;
keyword-hidden: spec never says race/lock/mutex/concurrency primitive).

## Fairness

Every verifier assertion quotes a visible spec bullet via `contract_refs`
(lint-fixtures enforced). Gateway latency is deterministic (trailing digits
of the id = ms), high-water threshold is stated in the spec with the exact
sample size, and the flip case is derivable from the visible settlement rule
alone. No hidden shape or tie-break exists outside spec.md.

## Headroom prediction (pre-registered, unmeasured)

bare ≤ 60 (expected to fail ordering-vs-completion or overlap), solo ≤ 80
(hypothesis: misses the decoupling — settles in completion order). To be
measured with `headroom-gate.py` before any pair-evidence claims; this
fixture carries no measurement claim until then.
