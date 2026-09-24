# 0220 — completion reserve after the 0219 D1 B breach (design)

**Status (2026-09-24): not launched; superseded by [0221](../../iterations/0221-subtraction-direction.md), which removes budget limits from tests.**

2026-09-24. The user asked to design a fix with Astra: root direct, no resolve.
Opus and Astra (gpt-6-astra/high, read-only) each wrote an independent R0. Astra
returned REVISE in round 1 on the wording only, and its wording is adopted
verbatim. Evidence is in `.devlyn/0220/`.

## Root cause

The [0219 screen](../0219/RESULT.md) stopped at D1-1-B with 420,832 input
against a 400,000 target. The product work and its review had passed. Why-chain:
- The breach came from two wrap-up generations: scope/hash audit, disposition
  and final report. Each re-sent the whole context, costing 34,141 and 35,134.
- Those generations did not fit. At the owner's last meter reading (351,557),
  only 48,443 remained.
- Planning missed this because the shared guidance reserves budget for checks,
  review and repair, but not for the final audit and report. The meter also
  shows totals only, so "keep enough" had no unit.

Violated invariant: budget planning must include all mandatory completion work,
plus unreported in-flight usage, before another round trip. The meter
arithmetic was correct.

## Fix (identical for A/B/C; owner texts untouched)

- [usage.py](usage.py) extends [0218's meter](../0218/usage.py) with
  `last_generation_input`: the latest completed owner generation's
  cache-inclusive input, taken from the accounting's validated `last` usage.
  It is advisory, not a guaranteed next cost. Totals are unchanged.
- [prepare.py](prepare.py) wraps [0219 preparation](../0219/prepare.py). It
  replaces the shared meter sentence with the completion-reserve sentence
  (`RESERVE`), which reserves only for work each arm's instructions already
  require. [run_cell.py](run_cell.py) is the 0219 runner with this preparation.
  A fresh control copy mounts the new meter at the same `/control/usage.py` path.

Not done: editing `0204/owner.md` (B's audit/report obligations are the
treatment), copying B's obligations into A/C, raising targets, changing models,
weakening checks, adding hooks, or compacting packets.

## Model-free evidence

- Meter replay (`meter-replay.txt`): on 9 archived 0218/0219 cells, totals
  are identical to the 0218 meter, and `last_generation_input` equals the
  rollout's final `last_token_usage` input. A setup-failed cell gives the same
  visible error. On 0219 D1 B prefixes with a duplicate cumulative record and a
  partial tail, generations 1, 13 and 14 read exactly. At the owner's real
  351,557 reading, the meter would have shown 32,950 per generation against
  48,443 remaining.
- Bindings (`dry/bindings.txt`): across all 24 cells, the prompt differs from
  0219 only by the replaced sentence. Bindings and provenance are correct, and
  repetitions are identical.

**Prediction:** comparable no-repair completions use fewer post-review
generations and less total input. If behavior is unchanged, the claimed
benefit is refuted. This is prevention by design, not a guarantee.

## Continuation

0219 stays stopped. Its cell 1 row stays historical and is not pooled. A new
registered 24-cell screen needs launch authorization; it reuses exposed D1–D4
development material and results are descriptive only. Before inference,
reseal admission: calibration, in-image public controls, format controls,
meter, bindings and account. Targets, models, order and the first-breach stop
rule are unchanged.
