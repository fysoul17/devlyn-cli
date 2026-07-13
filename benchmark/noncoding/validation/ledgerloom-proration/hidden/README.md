# ledgerloom-proration — why the bad packets are packet-decisive

Family: `CONTENT_CONSTRAINT_MUTATION` (both bad packets).

## The hinge

`task.txt` states five explicit content constraints on `prorate_cents`, each with
worked examples: integer cents only (a), round half up / never truncate (b), clamp
`days_used` into the period (c), `ValueError` on a non-positive period (d),
`TypeError` on a non-int amount (e). The oracle asserts exactly those seven worked
examples plus the two error cases. Each bad packet contradicts one of the
constraints and restates the affected worked example to match, so an agent that
follows the packet writes code that satisfies *the packet* and violates *the task*.

In both bad packets the task ids, the task array order, every `depends_on` edge,
every `context_refs` entry and every `scope` block are byte-identical to good-a.
Only content values move — `objective`, `acceptance[].observable` and
`project_acceptance[].observable` — plus the one `handoff` / `assumptions` line
needed to keep the packet from contradicting itself (narrative coherence carriers,
not part of the family signature).

The coding work is a five-line function either way. The difficulty is entirely in
whether the plan states the rule the task states.

## bad-1 — truncation instead of half-up rounding

Mutated values (all in-family):
- `t1-prorate.objective` rule (b): "round to the nearest cent with ties going away
  from zero (half up), reusing billing.money.round_half_up … never truncate" becomes
  "bill only whole cents that were fully earned: divide with integer floor division
  (//) so any fractional cent is dropped rather than rounded up".
- `t1-prorate.acceptance[a-2]`: 63 / 51 become 62 / 50.
- `t3-tests.acceptance[a-2]`: the same two numbers, so the tests the packet asks for
  pin the truncating behaviour.
- `project_acceptance[pa-2]`: the same two numbers.
- `assumptions[1]` (narrative): no longer claims proration routes through
  `round_half_up`, which would contradict the packet's own objective.

Causal chain: the agent writes `(amount_cents * billable_days) // days_in_period`.
`prorate_cents(125, 1, 2)` returns 62 and `prorate_cents(101, 1, 2)` returns 50. Its
own tests (which the packet told it to write against 62 / 50) pass, so the suite is
green. Oracle checks that fail: `prorate_cents(125, 1, 2) == 62, expected 63` and
`prorate_cents(101, 1, 2) == 50, expected 51` — both spelled out in task.txt as
"62.5 rounds up" / "50.5 rounds up". The non-tie examples (333, 451) are unaffected,
which is why the packet looks plausible.

## bad-2 — the clamp is dropped

Mutated values (all in-family):
- `t1-prorate.objective` rule (c): "clamp days_used to the period … so the charge
  never exceeds amount_cents and never goes below zero" becomes "prorate strictly by
  the days the caller reports: use days_used exactly as passed, so more days than
  the period bill proportionally more than amount_cents and negative days bill a
  credit".
- `t1-prorate.acceptance[a-3]`: 1000 / 0 become 1500 / -100.
- `t3-tests.acceptance[a-3]`: the same two numbers.
- `project_acceptance[pa-3]`: the same two numbers.
- `t1-prorate.handoff` (narrative): drops the "clamped to the period" claim.

Causal chain: the agent writes `round_half_up(amount_cents * days_used,
days_in_period)` with no clamp. `prorate_cents(1000, 45, 30)` returns 1500 — more
than the full charge — and `prorate_cents(1000, -3, 30)` returns -100, a credit. Its
own tests pass. Oracle checks that fail: `prorate_cents(1000, 45, 30) == 1500,
expected 1000` and `prorate_cents(1000, -3, 30) == -100, expected 0` — both spelled
out in task.txt as "clamped: never more than the full charge". Rounding is correct
here, so this is a genuinely different defect instance from bad-1: the two bad
packets fail on disjoint oracle checks.

## Verified

- seed base state: oracle FAILS (billing.proration does not exist).
- seed + `reference.patch`: oracle PASSES (suite 22 tests).
- simulated bad-1 implementation: its own suite passes, oracle FAILS on the two tie cases.
- simulated bad-2 implementation: its own suite passes, oracle FAILS on the two clamp cases.
