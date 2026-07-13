# cartwheel-rate-card — why the bad packets are packet-decisive

Family: `ORDERING_MUTATION` (both bad packets).

## The hinge

`data/rate_card.json` is a committed, generated artifact. Its only producer is
`python3 -m tools.build_rate_card`, which snapshots `rates/registry.py` **at the
moment it runs**. The task changes the registry in two independent ways (a new
ZONE_D entry, and the fuel surcharge 6 -> 9) and requires the committed card to
reflect both. So the refresh step is only correct if it runs *after* both registry
edits have landed. Nothing re-runs the generator later, and no test in the suite
reads the card — the staleness is silent at runtime and only the final repo state
shows it.

Good packets encode exactly that: the refresh task (`t3-refresh-card` in good-a,
`s-rate-card` in good-b) depends on both registry tasks and is presented after
them. Its objective/acceptance are deliberately order-neutral ("the committed card
is the generator's output for the registry"), so the *only* thing that decides
whether the card ends up correct is where the task sits in the plan.

## bad-1 — refresh between the two registry edits

Minimal mutation from good-a: `t3-refresh-card.depends_on` becomes
`["t1-zone-d"]` (was `["t1-zone-d", "t2-surcharge"]`), and the task array order
becomes `t1-zone-d, t3-refresh-card, t2-surcharge, t4-quote-tests`. Nothing else
in the packet changes.

Causal chain: the agent adds ZONE_D (t1), then runs the generator (t3) while
`FUEL_SURCHARGE_PERCENT` is still 6 — so the card is written with four zones but
`"fuel_surcharge_percent": 6`. It then raises the surcharge to 9 (t2) and updates
the tests (t4). The suite passes and the code is correct; the published card is
half-stale. Oracle checks that fail: `published rate card fuel_surcharge_percent
is 6, expected 9` and the generator-parity check `data/rate_card.json does not
match the generator's output for the current registry`.

## bad-2 — refresh before any registry edit

Minimal mutation from good-a: `t3-refresh-card.depends_on` becomes `[]`, and the
task array order becomes `t3-refresh-card, t1-zone-d, t2-surcharge,
t4-quote-tests`. Nothing else in the packet changes.

Causal chain: the agent runs the generator first (t3), against the untouched
registry — a no-op refresh that rewrites the old three-zone, 6% card. It then adds
ZONE_D, raises the surcharge and updates the tests. Final state: registry and
quotes correct, suite green, but the committed card is the original one. Oracle
checks that fail: the card lists only `['ZONE_A', 'ZONE_B', 'ZONE_C']`, its
`fuel_surcharge_percent` is 6, its ZONE_D entry is missing, and it does not match
the generator's output for the current registry.

## Why this is not code difficulty

Every code edit the task needs is trivial: one dict entry, one integer constant,
one command, a handful of test expectations. Both bad packets contain *all* of
those steps, with identical objectives, scope, acceptance and context_refs to the
good packet — they simply run the refresh at a moment when the registry is not yet
final. The failure is produced purely by the plan's order.

## Verified

- seed base state: oracle FAILS (no ZONE_D; card 3 zones / 6%).
- seed + `reference.patch`: oracle PASSES (suite 11 tests).
- simulated good-a execution order: oracle PASSES.
- simulated bad-1 order: oracle FAILS (card 4 zones / 6%).
- simulated bad-2 order: oracle FAILS (card 3 zones / 6%).
