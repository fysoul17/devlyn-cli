# F36 retired

Retired from the active golden suite after headroom run
`iter-0041-headroom-f36-f37`.

Reason: `solo_claude` scored 96, exceeding the headroom ceiling of 80, and
timed out doing so (full 1500s budget). bare scored 50 — the bare ceiling
held (headroom 10), and bare failed on the intended traps (wrong deferred-row
output shape: reason `capacity`/key `active` instead of
`over_capacity`/`blocking`, plus a validation miss). But solo's pipeline
still produced a scalable heap-based implementation that cleared the hidden
scale verifier, so there is no pair-lift headroom to measure. The
performance/scale axis alone does not hold the solo pipeline under 80.

Future use: the small-scale correctness traps discriminated bare as designed;
the scale verifier did not discriminate solo. A future rework needs a
difficulty axis that survives a full PLAN/BUILD_GATE loop, not just a
single-pass implementation.
