# F21 CLI scheduler priority

## Failure mode

This fixture detects implementations that pass simple scheduling tests while
missing interaction rules: global priority ordering, earliest-fit placement,
blocked-interval exclusion, half-open time boundaries, and deterministic output
ordering.

## Pipeline phase target

PLAN must preserve the ordering and interval invariants. IMPLEMENT must build a
small scheduling engine without adding dependencies. VERIFY should catch
counterexamples where local request order or naive overlap checks produce a
plausible but wrong schedule.

## Why existing fixtures do not cover it

F16 covers checkout arithmetic. F10/F11/F12/F15 cover server behavior. None
exercise a CLI algorithm where the correct result depends on sorting,
interval arithmetic, and output ordering at once.

## Measurement status

Pair evidence passed in `20260511-f21-current-riskprobes-v1`: bare `33`,
solo_claude `66`, pair `99`, margin `+33`, wall `1.47x`,
arm `l2_risk_probes`, verdict `pair_evidence_passed`.

## Solo-headroom hypothesis

A capable solo_claude baseline is expected to miss global priority ordering
combined with blocked-interval earliest-fit placement; observable command
`node "$BENCH_FIXTURE_DIR/verifiers/priority-blocked.js"` exposes the miss.

## Retirement

Retire or replace when both bare and solo consistently exceed the headroom
thresholds, or if future fixtures cover the same interval-scheduling failure
mode with better discrimination.
