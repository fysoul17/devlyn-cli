# F35 CLI apply journal

## Failure mode

Detects implementations that flatten the composite ordering/replay/atomicity
contract into the easy shape: apply-in-file-order against pre-batch stock
with per-row persistence. Three discriminators: (a) `applied` order and
journal append order must follow priority-desc with file-order ties (final
quantities alone cannot catch this — addition commutes); (b) the failing
op's `available` is measured at its turn AFTER higher-priority ops changed
stock (rollback verifier: 15, not the pre-batch 10); (c) any failure leaves
both files byte-for-byte unchanged. In-file duplicate `op_id` is a
validation error while a journaled `op_id` is a per-op skip — the
distinction is the replay axis (Tier-1 "A1" from memory
`project_pair_fixture_tier1_2026_05_05`; keyword-hidden: spec never says
atomic/transaction/idempotent/rollback).

## Fairness

Every verifier assertion quotes a visible spec bullet via `contract_refs`
(lint-fixtures enforced). Verifiers reset the seeded files before running so
command order cannot leak state between checks. No hidden shape, tie-break,
or availability rule exists outside spec.md.

## Headroom prediction (pre-registered, unmeasured)

bare ≤ 60 (expected to miss at-its-turn availability or journal append
order), solo ≤ 80 (hypothesis: evaluates availability against pre-batch or
file-order state). To be measured with `headroom-gate.py` before any
pair-evidence claims; this fixture carries no measurement claim until then.
