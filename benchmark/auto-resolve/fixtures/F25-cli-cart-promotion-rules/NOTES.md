# F25 CLI cart promotion rules

## Failure mode

This fixture detects checkout implementations that pass shallow cart tests while
missing interaction invariants: duplicate-SKU aggregation, line-promotion order,
order-coupon order, taxable base selection, free-shipping threshold timing, and
externalized catalog data.

## Pipeline phase target

PLAN must preserve ordering between aggregation, validation, line promotions,
coupon discount, tax, and shipping. IMPLEMENT must keep all money values in
integer cents without new dependencies. VERIFY should execute adversarial cart
examples rather than only checking a happy path.

## Why existing fixtures do not cover it

F16 covers quote tax rules, but not multiple line-promotion types plus an order
coupon. F21/F23 cover scheduling/allocation, not checkout interaction ordering.
This fixture keeps the F16-style fair visible-contract shape while testing a
different checkout interaction.

## Measurement status

Pair evidence passed in `20260510-f16-f23-f25-combined-proof`: bare `25`,
solo_claude `75`, pair `99`, margin `+24`, wall `1.65x`,
arm `l2_risk_probes`, verdict `pair_evidence_passed`.

## Solo-headroom hypothesis

A capable solo_claude baseline is expected to miss the interaction between
duplicate aggregation, line promotions, tax base, coupon order, and shipping;
observable command `node "$BENCH_FIXTURE_DIR/verifiers/exact-success.js"` exposes the miss.

## Retirement

Retire or replace this fixture if either `bare` or `solo_claude` consistently
reaches ceiling, or if a later fixture covers the same promotion-order and
catalog-source failure mode with cleaner full-pipeline lift.
