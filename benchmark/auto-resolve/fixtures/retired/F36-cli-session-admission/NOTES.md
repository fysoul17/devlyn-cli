# F36 Session admission command with a global concurrency cap

## Failure mode

Detects implementations that get interval-admission logic correct at small,
hand-written scale but reach for a data structure that stops scaling once
the number of concurrently active sessions grows large — most naturally, a
plain array of admitted sessions that gets linearly scanned or filtered on
every new candidate. That shape is indistinguishable from the fully correct
answer on any test an agent is likely to hand-write, and only fails once the
active set stays large across a long run (Tier-2 axis: performance/scale,
never previously used in this suite — no existing fixture verifier measures
wall-clock; grepped `verifiers/*.js` across active + retired fixtures for
`Date.now|hrtime|performance.now|elapsed`, zero hits before this one).
Compounded with four small-scale correctness sub-traps so a fast-but-wrong
shortcut and a correct-but-slow shortcut both lose points independently:
half-open boundary (touching, not overlapping), start-time eligibility
order vs. file order, per-candidate (not static) `active_at_start`, and
eviction that must be driven by actual expiry (`end`) rather than admission
order — the last one specifically closes a FIFO-queue shortcut that would
otherwise pass the scale case by coincidence, since the scale case uses a
uniform session duration and a FIFO queue's admission order happens to
coincide with its expiry order there (Codex R2 catch, see Rounds below).

## Fairness

Every verifier assertion quotes a visible spec.md bullet via `contract_refs`
(lint-fixtures enforced). The 150,000-session performance requirement is
stated as a plain, numeric, visible spec bullet — no mechanism vocabulary
(no "sort", "heap", "priority queue", "efficient", "O(n log n)") appears
anywhere in `spec.md` or `task.txt`; only the observable behavior (must
finish within the process timeout, must not change the answer) is named.
The scale verifier's 15-second hard kill (`spawnSync` `timeout` option) sits
more than 100x above the efficient reference's actual running time and
correspondingly far below any realistic degraded-shortcut running time on
this fixture's parameters, so the gate has a wide, non-flaky margin in both
directions.

## Pipeline phase(s) tested

BUILD_GATE / VERIFY: an agent's own test suite is overwhelmingly likely to
be small-N (a handful of hand-written sessions), so nothing in a normal
iterative dev loop surfaces the scale defect; only the hidden, harness-side
scale verifier (never visible to the arm) exercises it. This is a
structurally different discriminator from every prior fixture in this
suite, which relied entirely on a single hidden semantic trap rather than a
mechanical, orthogonal performance axis.

## Why another fixture can't cover this

No active or retired fixture in this suite measures wall-clock/algorithmic
complexity at all (verified by grep, see Failure mode above). Every prior
headroom attempt (F27, F28, F30, F34, F35, S2-S6 — see
`pair-rejected-fixtures.sh`) relied on a single hidden ordering/rollback/
atomicity trap, and solo_claude scored 88-100 on all of them. This fixture
tests a category of miss (asymptotic complexity blindness under a full
self-review pipeline) that none of those exercise.

## When to retire or replace

If a headroom run shows solo_claude reliably recognizes and implements the
required efficient structure even without prompting (i.e. the visible
numeric scale requirement alone is enough to trigger scale-aware design),
retire per the same honest-retirement contract used for F27/F28/F30/F34/F35
and add this id to `pair-rejected-fixtures.sh` with the observed scores.

## Rounds — Codex GPT-5.5 collaboration (read-only, `codex-monitored.sh`)

**Round 1** (initial design: performance stated as a secondary condition on
top of a single hidden ordering trap, textbook "meeting rooms with
capacity" shape): Codex verdict **needs-rework** — "200,000 sessions" alone
is enough for a strong PLAN phase to infer scale pressure and pattern-match
the well-known interval-scheduling/heap shape; the boundary traps alone
weren't judged sufficient given solo already solved comparable explicit
order/rollback traps in F34/F35. Adopted: make performance the dominant
axis by choosing scale-case parameters (uniform long overlapping durations,
capacity held well below the overlap window) so that BOTH a brute
nested-loop AND a "linear-scan a plain active-sessions array" middle-tier
shortcut fail — only a genuinely sub-linear-per-op structure survives, not
merely "some awareness of scale."

**Round 2** (revised design presented): Codex verdict **converge, with one
fix** — flagged that because the scale case uses a uniform session
duration, admission order and expiry order coincide, so a FIFO
queue-with-front-eviction (simpler than the general answer, and not the
"real" discriminator intended) would also pass the scale case correctly and
fast. Fix adopted: added the fourth small-scale correctness sub-trap
(eviction driven by actual smallest `end` among currently active sessions,
not admission order) via a hand-authored 3-session case where a FIFO
shortcut and the correct rule disagree. This closes the loophole without
touching the scale case's parameters, since the two verifiers are
independent files/inputs.

Codex's own words, R2 answer to Q1: "F36 is much stronger now, but I see one
real shortcut left: a FIFO/sliding-window queue of admitted sessions can
pass the scale case if ends are monotonic... Add one small correctness case
where admitted end order differs from start/admission order... That defeats
FIFO while keeping the scale discriminator intact." Adopted verbatim as
correctness sub-trap 4.
