# iter-0039 — /devlyn:queue utility + Tier-1 headroom fixtures (F34, F35)

**Status**: STAGED — fixtures pre-registered and mechanically validated;
headroom measurement (paid arm runs) is the queue's first item, next session.
**Trigger**: explicit user direction 2026-07-03: ship `/devlyn:queue` (one skill,
not queue+drain two — the queue and its lifecycle are one concept; the drain
DRIVER is replaceable: this skill today, devlyn-os daemon later, both over the
same `docs/specs/queue.md` file contract) and "벤치마크도 더 어려운 것까지
준비" — the evolution loop's bottleneck is fixture saturation
(feedback_pair_measurement_needs_headroom binding).

## Shipped

1. **`/devlyn:queue`** (status / `add` / `drain`): pure front-end over the
   CLAUDE.md intent-queue contract (iter-0037 C5). No new semantics → no new
   Codex round (same rationale as `/devlyn:engines`). Added to
   `DEVLYN_CORE_SKILLS`; lint literal pin updated.
2. **F34-cli-settle-inflight** (Tier-1 "H1"): overlapping async gateway
   authorizations (`high_water >= 3` visible requirement) DECOUPLED from
   strict file-order settlement. Keyword-hidden (no race/lock/mutex).
3. **F35-cli-apply-journal** (Tier-1 "A1"): priority-order application with
   at-its-turn stock evaluation, journal replay-vs-in-file-duplicate
   distinction, all-or-nothing byte-identical persistence. Keyword-hidden
   (no atomic/transaction/idempotent/rollback).

## Validation record (this session, no paid arms)

- `scripts/lint-fixtures.sh` PASS — contract_refs exact-substring rule enforced.
- Reference implementations: 5/5 verifiers `ok:true` (hand-computed expected
  values confirmed: F34 balances a=155/b=0/c=0/d=5, t-40 rejected available=30;
  F35 applied order op-2,op-3,op-1,op-4, journal append, rollback available=15).
- Falsification: sequential-await F34 impl caught (high_water=1 → fail);
  file-order F35 impl caught (available=10 ≠ 15 → fail).
- Originally staged as F30/F31 — renamed F34/F35 after `benchmark audit-headroom`
  flagged short-id collisions with the rejected-fixture registry (F30 and F31
  were already burned by past failed headroom candidates; rejected ids are
  never reused).
- Codex fairness audit (hidden-oracle / solo-ace / bare-ace / verifier-bug /
  flakiness axes): see R-fairness record below.

## Pre-registered predictions (unmeasured — measure BEFORE trusting)

- P1: F34 bare ≤ 60, solo ≤ 80 (miss: completion-order settlement).
- P2: F35 bare ≤ 60, solo ≤ 80 (miss: at-its-turn availability under
  priority order).
- Gate: `python3 benchmark/auto-resolve/scripts/headroom-gate.py` on a
  bare+solo run pair per fixture, wired through
  `run-full-pipeline-pair-candidate.sh` (bare/solo first; l2 spend only after
  headroom passes). If either fixture fails headroom or fairness on real
  arms, retire it honestly (F17-F29 precedent) — do not tune the oracle to
  pass.

## R-fairness record (Codex, 2026-07-03)

Verdict: both fixtures **BUGGY** on one shared class — `JSON.stringify`
equality made JSON object property order a hidden oracle narrower than the
visible contract (spec requires exact keys/values and array order, not
property insertion order). Fixed: three verifiers now use structural
deep-equality (object key order ignored, array order strict); byte-for-byte
checks kept only where the spec explicitly requires them (F35 failure-path
files). Second finding adopted: `calls === 6` assertion gained its
contract_ref ("authorize ... exactly once per transfer"). Codex confirmed:
all math correct, all contract_refs exact substrings, keyword hygiene clean
(NOTES.md giveaways acceptable — not in solver prompts), `high_water >= 3`
low-flake (synchronous increment before timer). Post-fix: 5/5 verifiers
re-validated against reference implementations.

## Placement

Staged at `benchmark/auto-resolve/fixtures/staging/` — invisible to
lint-fixtures and the frontier audit (both enumerate top-level `F*` only),
because the packaged audit fails on `candidate_unmeasured` by design and
measurement is deferred to the next session's queue drain. Activation
contract in `staging/README.md`. Also renamed from F30/F31 after the
headroom-rejections audit flagged short-id collisions with the rejected
registry.
