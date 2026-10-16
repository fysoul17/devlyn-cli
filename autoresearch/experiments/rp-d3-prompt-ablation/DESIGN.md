# rp-d3 design — prompt ablation

rp-d1 and the rp-d2 rerun ([results](../rp-d2-report-lines/results.md))
found the same thing. Codex delivered correctly every time, but its final
report never named cleanup, and it usually gave only "the checkout is clean"
for reconciliation. Codex's report passed in 0/4 rp-d1 slots and in 0/4 rerun
slots (0/2 per arm). rp-d2's product paragraph (arm Y) did not change that
shape. Grok's recorded dissent ([rp-d2 DESIGN.md](../rp-d2-report-lines/DESIGN.md))
is that the benchmark prompt's closing sentence sets Codex's report shape.
rp-d3 tests that dissent, which rp-d2 registered as its next candidate.
Design reviews (round 0, both REVISE; every finding is applied below):
[Astra](results/design-r0-astra.md), [Grok](results/design-r0-grok.md).

## Question

Is Codex's report shape sensitive to the prompt's closing sentence on BV/Z0
under 4.2.18? This is an exploratory routing screen for the next candidate,
not a causal confirmation.

## Mechanism

The product is fixed: the published `devlyn-cli@4.2.18` registry tarball
(rp-d2 arm X, SHA-256 `7b22cce8…393e`; its `task-completion.md` equals blob
`7516ebc9`). Only the task prompt body
([common.txt](../rp-d1-delivery-cost/common.txt)) differs.

- **P0 (control):** `common.txt` unchanged.
- **P1 (ablation):** `common.txt` with exactly the suffix
  ` Finish with what you changed, what you verified and anything unresolved.`
  removed (its leading space included), the trailing newline kept, and
  nothing added.

Both arms append the same `\nCALLER CONTRACT\n` and `caller.json`. Both
prompt-body hashes are registered. The other sentences stay on both arms;
they are shared, so they do not bias the contrast.

`task-completion.md:203` still says "Report verification, delivery and
checkout reconciliation separately". It does not name cleanup, while the
grader requires a cleanup claim. The rest of the skill still describes
cleanup and reconciliation. That is a known interpretation limit, not a
confound between arms.

## Scope

**Codex only** (Codex 0.162.1, `gpt-6-sol`, effort high, the rp-d2 image
definition). Claude passed every graded report under P0 (rp-d1 3/3, rerun
3/3), and every rp-d2 STOP came from a Claude connection drop. rp-d3 leaves
`common.txt` unchanged whatever the outcome. Any later change to the shared
benchmark prompt gets its own registered check, including Claude quality and
cost.

## Schedule

Tasks BV and Z0 (rp-d1 `tasks.json`), two repetitions each, paired and
interleaved. P0 runs in slots 1, 4, 5 and 8 and P1 in 2, 3, 6 and 7.

| Pair | Task | Order |
|---|---|---|
| 1 | BV | P0, P1 |
| 2 | BV | P1, P0 |
| 3 | Z0 | P0, P1 |
| 4 | Z0 | P1, P0 |

Eight measured slots `m01`–`m08`; they are never replaced.

**Smoke.** Two Codex cells on SM, one P0 and one P1. One registered spare
attempt repeats both cells, and a stopped smoke is discarded as a pair.
Smoke qualifies delivery, the prompt-hash binding, the single-tarball
binding and checklist emission. Smoke reports are not graded, and smoke
results never change the prediction, the arms or the thresholds. That is 12
repositories: 8 measured, 2 smoke and 2 spare.

## Grading

Unchanged from rp-d2. Delivery is graded mechanically. A report passes only
when Astra ultra and Grok 4.7 both find all four categories (verification,
merge, cleanup, reconciliation) SUPPORTED against the slot's frozen
checklist. The summary also tallies, per arm, the slots in which both
reviewers found cleanup SUPPORTED and the slots in which both found
reconciliation SUPPORTED, and it lists each pair's outcomes.

## Prediction (frozen at registration, before smoke)

> Removing the closing sentence (P1) raises Codex's report success over P0 on
> BV/Z0 under 4.2.18, with every delivery passing.

## Decision

Attribution needs all eight slots dispatched, every delivery passing and
every report adjudicated by both reviewers. Otherwise the result is
INCONCLUSIVE, and a STOP overrides every branch.

- **PROMPT-SENSITIVE:** P1 report ≥ 3/4 and P0 report ≤ 1/4. The sentence
  blocks Codex's four-category report on these tasks. Next: a registered
  benchmark-prompt change with its own Claude check (owner decision).
- **NO RESCUE:** P0 report ≤ 1/4, P1 report ≤ 1/4, P1 cleanup ≤ 1/4 and
  P1 reconciliation ≤ 1/4. The historical outline survived the deletion.
  Next: a product reporting candidate.
- **MIXED:** every other pattern. Follow-ups:
  - P1 cleanup ≥ 3/4 with P1 report ≤ 2/4: follow the category that still
    fails.
  - P1 reconciliation ≥ 3/4 with P1 cleanup ≤ 1/4: measure the rp-d2 Y
    cleanup paragraph with this sentence still absent.
  - P0 report ≥ 2/4: no attribution.

A 3/4 against 0/4 table has a one-sided Fisher p of about 0.07. The
thresholds are gates for the next experiment, not proof.

Cost (tokens, wall time) is recorded per arm and reported descriptively.

## Apparatus

A new directory reusing the rp-d2 runner, with these inverted checks:

- **One artifact.** Every slot installs the one verified X tarball; a check
  before sealing confirms the installed `task-completion.md` equals blob
  `7516ebc9`. rp-d2's two-release and "trees differ by exactly one file"
  checks are dropped.
- **Prompt binding.** The arm selects only the prompt body. P1 is derived
  from `common.txt` by the exact deletion above and checked against its
  registered hash. Each verdict records `prompt_sha256` and the release
  SHA-256, and the runner fails the slot if either disagrees with its arm.
- **Codex only.** The 8-slot schedule, the two smoke cells and spares, the
  repository names and a new summarizer with the decision rules above
  replace rp-d2's. No Claude credential or Claude boot catalog is required.
- **Frozen inputs.** One image digest, CLI/model configuration, models cache
  and Codex account across both arms. Fresh run ID, repositories and PAT.
  Benchmark hard rule 5 applies: the host network is held fixed and the VPN
  client is quit for the run.

## Interpretation limits

Four slots per arm on two tasks, one product version and one model. A
PROMPT-SENSITIVE result does not show the product rule is sufficient in
general, and a NO RESCUE result does not show the product rule is wrong.
Server-side model drift since rp-d1 is uncontrolled; contemporaneous P0 is
the baseline.
