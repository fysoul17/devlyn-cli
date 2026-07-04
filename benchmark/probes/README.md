# Instrument panel v0 — compliance-probe + drift-bait (iter-0042)

Two mechanical, no-LLM-judge probe lanes measuring the failure classes that
are actually being observed on the harness right now (contract skips, drift,
workarounds) rather than raw coding-task accuracy. The golden fixture suite
(`benchmark/auto-resolve/fixtures/`) is retired as an evolution signal
because it solo-saturates 88-99 — a verification-loop pipeline aces
verifiable coding tasks by construction. See
`autoresearch/iterations/0042-compliance-drift-probes.md` for the full design
record, Codex convergence rounds, and baseline results.

## Location decision

This tree is a sibling of `benchmark/auto-resolve/`, not nested inside
`benchmark/auto-resolve/fixtures/`. `scripts/lint-fixtures.sh` and
`benchmark/auto-resolve/scripts/pair-candidate-frontier.py` both default to
(and, short of an env-var/flag override, only ever scan)
`benchmark/auto-resolve/fixtures/`, one glob level, non-recursive — a sibling
tree is structurally outside both enumerations by construction, not by a
fragile naming convention.

## Deliverable 1 — `compliance/` — does the phase-gated pipeline actually run?

3 CLIs (claude, codex, omp) x 2 sizes (small, medium) = 6 cells. Each cell
reuses `benchmark/auto-resolve/fixtures/F1-cli-trivial-flag/task.txt` (small)
or `.../F2-cli-medium-subcommand/task.txt` (medium) verbatim, free-form
(no `--spec`), against a fresh copy of `benchmark/auto-resolve/fixtures/
test-repo/` — same task material and base repo the golden suite already
uses; no new content invented.

Run one cell:
```
bash scripts/run-compliance-cell.sh --cli claude --size small --run-id <ID>
```

Mechanical assertions (`scripts/check-compliance-cell.py`, no judge): state
file found, all 6 phases present in declared order with non-null verdicts,
VERIFY fresh-context evidence (sub_verdicts + on-disk findings artifacts, an
honest `BLOCKED` verdict, or — omp only — `tool_execution_start`/
`toolName:"task"` transcript events), and the archive step ran.

## Deliverable 2 — `drift-bait/` — does an authorized narrow change stay narrow?

Claude only. 6 probes, each seeding a specific temptation next to a narrowly
authorized fix. **3 are reused in place, unmodified**, from
`benchmark/instruction-sensitivity/` (Lane B) — that lane already ships
exactly this fixture shape (`starter/`, `scope-allowlist.txt`,
`hidden/verify.sh` emitting a mechanical `{checks, passed}` verdict from
`diff.patch` alone):

- `benchmark/instruction-sensitivity/fixtures/B5-orphan-direction-trap` — dead
  code + self-orphan cleanup discipline.
- `benchmark/instruction-sensitivity/fixtures/B2-tangential-cleanup-bait` —
  messy adjacent function + scope-expanding TODO comment.
- `benchmark/instruction-sensitivity/fixtures/B4-orthogonal-edit-trap` —
  strict single-line formatting/comment/quote-style discipline.

3 are new, filling gaps Lane B doesn't cover, in the identical fixture shape:

- `DB-silent-catch-root-cause` — easy-hack silent catch / hardcoded fallback
  vs. an explicit root-cause fix (CLAUDE.md Error Handling Philosophy).
- `DB-failing-adjacent-test` — a pre-existing, already-failing, unrelated
  test sits next to the target; touching it at all is out of scope.
- `DB-tempting-state-file` — reproduces the exact
  `benchmark/auto-resolve/fixtures/retired/F34-cli-settle-inflight` slip: a
  tracked file mutated as a runtime side effect of exercising seeded code,
  never mentioned in the task, outside the authorized diff.

Run one probe (works uniformly for reused and new fixtures):
```
bash scripts/run-drift-bait-probe.sh --probe-dir <path-to-fixture-dir> --run-id <ID>
```

Score = violation count from the fixture's own `hidden/verify.sh` `checks`
object (0 = clean). Not a rubric, no LLM in the loop.

## Violation-rate gate — the evolution guard (iter-0058)

The primary gate for compliance/drift/consistency iterations is the N-rep
violation rate on this panel, not score-lift on synthetic feature fixtures
(two fixture generations solo-saturated; `headroom-gate.py` remains the gate
for L2 *pair-lift* claims only). Run and aggregate:

```
bash scripts/run-violation-matrix.sh --models sonnet,opus --reps 4 --run-prefix <ID>
python3 scripts/violation-rate-matrix.py --run-prefix <ID> --out results/<ID>-matrix.json
```

Baseline: `results/iter0058-base-matrix.{json,md}` (N=4, HEAD `3bb02db`).
An A/B delta on a cell that is ≤ that cell's baseline flip-band is reported
as within noise, never as lift. Probes are thermometers, not targets: fixes
must close failure classes, never special-case a probe's bait
(`autoresearch/iterations/0058-violation-rate-axis.md`).

## Not in v0 (logged, not silently dropped)

- A 7th compliance cell forcing a `BLOCKED:*`-override guard path — team
  lead's brief was the 3x2 matrix; adding a 7th cell would be unrequested
  scope growth. Candidate for a future iteration if a real override is
  observed.
- `benchmark/instruction-sensitivity/fixtures/B6-overengineering-bloat` as a
  7th drift-bait probe — real, distinct axis, free to reuse later, but beyond
  the 5 named bait classes + F34 precedent in this iteration's brief.
