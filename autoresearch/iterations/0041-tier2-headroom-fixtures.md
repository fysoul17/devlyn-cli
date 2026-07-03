# iter-0041 — Tier-2 headroom fixtures (F36, F37): performance/scale axis

**Status**: STAGED — fixtures designed, Codex-converged, and mechanically
self-validated (reference + lazy candidates); headroom measurement (paid
bare + solo_claude arm runs) is deferred to a future session per the
staging contract.
**Trigger**: `docs/specs/queue.md` item 2 (engine cross-mix measurement),
blocked because no fixture has ever passed the headroom gate (bare ≤ 60,
solo ≤ 80). Tier-1 (F34/F35, iter-0039) both failed headroom
(`iter-0039-headroom-f34-f35`): F34 bare 92 (task too easy even bare); F35
bare 50 but solo 97 (spec leaked enough for a full pipeline to ace it).

## Base rate this design had to beat

Every fixture ever measured in this suite — ~24 across F1-F35 plus shadow
S2-S6 — has failed the headroom gate. `solo_claude` scored 88-100 on
literally all of them (see `benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh`
for the full scored registry), including fixtures with a carefully
keyword-hidden single semantic trap (concurrency decoupling, atomic
rollback, priority tie-break with rollback). Grepped every active + retired
fixture's `verifiers/*.js` for `Date.now|hrtime|performance.now|elapsed`:
**zero hits** before this iteration — no fixture in the suite's history has
ever measured wall-clock or algorithmic complexity. That gap is this
iteration's chosen axis.

## Shipped (staged, not activated)

1. **F36-cli-session-admission**: interval admission against a global
   concurrency cap. Compound design — four small-scale correctness
   sub-traps (half-open boundary, start-order-not-file-order eligibility,
   a `blocking` field requiring correct per-candidate active-set tracking,
   and an eviction-order trap that specifically defeats a FIFO-queue
   shortcut) plus a scale verifier (150,000 sessions, capacity held below
   the natural overlap peak but above `n`) that forces a genuinely
   sub-linear-per-op structure — a brute nested loop or a "linear-scan the
   active array" middle-tier shortcut both cost ~1.35e10 element touches at
   these parameters; the efficient (heap-based) answer finishes in well
   under a second. 15-second hard kill via `spawnSync({timeout})`.
2. **F37-cli-rule-lookup**: point-in-time ("as-of") pricing-rule lookup —
   each of 200,000 events must resolve the rule revision in effect for its
   category at its own timestamp, against 60,000 revisions across 4
   categories (15,000/category) in the scale case. Naive per-event linear
   scan (whether over all revisions or just its own category's unsorted
   list) costs ~2-12e9 comparisons; grouped + sorted + binary-searched is a
   few million log-steps. Same 15s hard-kill pattern. Small-scale
   correctness sub-traps: inclusive `effectiveAt <= timestamp` boundary,
   same-`effectiveAt` tie-break (greatest `id`), and
   `unknown_category`-vs-`no_effective_rule` distinction.

Both are pure `bin/cli.js` + `tests/cli.test.js` diffs against
`test-repo`, high-risk category (scheduling / pricing risk-trigger terms),
1500s arm timeout. No mechanism vocabulary (heap, sort, binary search,
efficient, O(n log n)) appears anywhere in either `spec.md` or `task.txt` —
only observable, numeric performance requirements, matching the suite's
existing keyword-hiding discipline for semantic traps.

## Codex GPT-5.5 collaboration (read-only, `codex-monitored.sh`, xhigh/high effort)

**Round 1** (initial designs — F36 performance stated as a secondary
condition on a textbook "meeting rooms with capacity" shape; F37 was a
multi-hop category-merge chain + dual-file rollback + idempotent-rerun
design): verdict F36 **needs-rework**, F37 **reject-and-replace**.
- F36: "200,000 sessions... is enough for a strong PLAN phase to infer
  scale pressure and pattern-match the well-known interval-scheduling/heap
  shape." Adopted: construct the scale case so a middle-tier
  "scale-aware-but-not-fully-efficient" shortcut also fails, not just brute
  force.
- F37: "It reads like F35/F26/F32 with new nouns... solo already scored
  97-98 on these families." Adopted Codex's concrete counter-proposal
  wholesale: an as-of point-in-time lookup at scale, replacing the
  rollback/idempotency shape entirely.

**Round 2** (revised designs): verdict **converge, one fix** — flagged that
F36's uniform-duration scale case makes admission order and expiry order
coincide, so a FIFO-queue shortcut (not the intended O(log n) structure)
would also pass the scale case by coincidence. Fixed by adding a fourth
small-scale correctness sub-trap (non-monotonic admission-vs-expiry order)
that a FIFO shortcut fails regardless of the scale case's parameters. F37
confirmed as-is: "a different access pattern... I would not call it a
freebie in the same way as 'meeting rooms'."

Full transcripts and per-round deltas recorded in each fixture's NOTES.md
(`benchmark/auto-resolve/fixtures/staging/F36-cli-session-admission/NOTES.md`,
`.../F37-cli-rule-lookup/NOTES.md`).

## Self-validation record (this session, no paid arms)

Built a faithful replica of `run-fixture.sh`'s verification block (same
`BENCH_WORKDIR`/`BENCH_FIXTURE_DIR` env, same exit_code/stdout_contains/
stdout_not_contains checks, same 60s per-command outer timeout) and ran it
against hand-written reference and lazy `bin/cli.js` candidates copied into
a fresh `test-repo` + `setup.sh` work tree (never committed to the
fixtures):

| Fixture | Candidate | correctness-small | validation | scale | Result |
|---|---|---|---|---|---|
| F36 | reference (heap + admission-order Map) | PASS | PASS | PASS | all 4 verification_commands pass |
| F36 | lazy FIFO-front-eviction | **FAIL** (non-monotonic-eviction) | PASS | PASS (15,005ms, coincidentally fast+correct there) | caught by small-scale, not scale |
| F36 | lazy linear-scan active array | PASS | PASS | **FAIL** (TIMEOUT, SIGKILL @ 15,006ms) | caught by scale, not small-scale |
| F37 | reference (group+sort+binary search) | PASS | PASS | PASS | all 4 verification_commands pass |
| F37 | lazy per-event full linear scan | PASS | PASS | **FAIL** (TIMEOUT, SIGKILL @ 15,006ms) | caught by scale only |

This is the intended discrimination shape: a correct-and-efficient
implementation passes everything; a fast-but-subtly-wrong implementation is
caught by the small-scale correctness verifier; a correct-but-naive
implementation is caught only by the scale verifier. No single verifier is
redundant with another.

## Placement

Staged at `benchmark/auto-resolve/fixtures/staging/{F36-cli-session-admission,F37-cli-rule-lookup}/`
— invisible to `lint-fixtures.sh` and the frontier audit by design (both
enumerate top-level `F*` only). Confirmed: `bash scripts/lint-fixtures.sh`
still reports the pre-existing 21 active / 6 retired count, unaffected by
the new staging subdirectories. Activation contract in
`fixtures/staging/README.md` (move up → lint → bare+solo arms →
`headroom-gate.py`, bare ≤ 60 / solo ≤ 80, both clean → retire honestly on
FAIL, never tune the oracle to pass). F36/F37 are the next fixture ids
after F35 (highest ever used, including retired/rejected) — no id reuse.

## Pre-registered predictions (unmeasured — measure BEFORE trusting)

- P1 (F36): bare ≤ 60 (misses at least one of the four small-scale
  sub-traps, or ignores scale entirely), solo ≤ 80 (BUILD_GATE's own tests
  are overwhelmingly likely to be small-N, so nothing in the normal
  iterative loop surfaces the scale defect).
- P2 (F37): bare ≤ 60, solo ≤ 80, same reasoning — the lookup structure
  that's correct-at-small-scale is not the one that stays fast at
  60,000-revisions-per-category-adjacent scale.
- Gate: `python3 benchmark/auto-resolve/scripts/headroom-gate.py` on a
  bare+solo run pair per fixture. If either fails headroom, retire honestly
  (F27/F28/F30/F34/F35 precedent) and add to `pair-rejected-fixtures.sh` —
  do not tune the oracle to pass.

## Risk flagged, not resolved

Codex's own residual doubt (R1 answer to Q1, before the R2 fix): a strong
coding model may still infer scale-awareness from the visible numeric
requirement alone and implement the correct structure on the first try
without ever having needed the pressure test. This is empirically
unfalsifiable without a real paid measurement — flagged here rather than
assumed away, consistent with `feedback_pair_measurement_needs_headroom`
(no pair-mode iter ships on unmeasured headroom claims).
