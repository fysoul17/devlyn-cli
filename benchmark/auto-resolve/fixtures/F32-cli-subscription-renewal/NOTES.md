# F32 Subscription renewal command

## Failure mode

This fixture targets billing-style state mutation where an implementation can
look correct on isolated cases but fail the interaction between renewal
priority, tentative credit application, rollback after `payment_required`, exact
credit consumption order, and strict JSON row shapes.

## Pipeline phase coverage

- PLAN must preserve the exact input/output field names and ordering clauses.
- RISK_PROBES should derive a compound priority + rollback + shape probe.
- IMPLEMENT must avoid input-order processing and must not leak tentative credit
  consumption from rejected renewals.
- VERIFY pair mode should catch aliased keys, extra keys, and weak tests that
  check only one field rather than the full parsed output.

## Why existing fixtures do not cover it

F25 covers pricing math and output shape, F31 covers entitlement transfers and
duplicate-id errors, and F23 covers fulfillment rollback. F32 combines billing
credits with a failed high-priority renewal that must roll back before a later
renewal can consume credits, plus exact nested output key sets.

## Retirement criteria

Retire or replace this fixture if both `bare` and `solo_claude` score above 95
on two current-model runs, or if another active fixture covers priority-ordered
tentative monetary credit rollback with exact nested output shape and duplicate
ID error contracts.

## Pair-candidate status

Rejected as pair-lift evidence by `20260512-f32-subscription-renewal-headroom`:
bare scored 33, but solo_claude scored 98 and passed all 3 verification
commands. Keep it as a billing rollback/shape control, not as a pair arm target,
unless it is reworked and clears a fresh headroom gate.
