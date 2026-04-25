# Iteration playbook

Run this loop once per hypothesis. Estimated time: an hour for a narrow change with a fixture-subset re-run; a workday for a full-suite ship gate.

---

## Section 1 — PROPOSE

**Pick the next hypothesis.** Open `autoresearch/README.md` and take the top item from the "Next hypotheses (ordered)" section. If you came in with a different idea, prepend it to that list first and explain why it deserves the top slot — never silently jump the queue.

**Create the iteration file.** Number it the next integer after the last entry in `iterations/`. Slug = three-to-five lowercase words.

```bash
ls autoresearch/iterations/ | sort -n | tail -3
# pick NNNN as last + 1
touch "autoresearch/iterations/NNNN-<slug>.md"
```

**Fill in the schema** (use this exact template; later sections will reference these section names):

```markdown
# NNNN — <one-line hypothesis statement>

**Status**: PROPOSED | RUNNING | SHIPPED | REVERTED | BLOCKED
**Started**: YYYY-MM-DD
**Decided**: YYYY-MM-DD (or empty)

## Hypothesis

One sentence stating the metric direction. Example: "F3 fixture's margin will move from −10 to ≥+5 because the test-fidelity rule the variant arm currently bypasses will be enforced by EVAL after this prompt change lands."

## Mechanism

Why we expect the hypothesis to hold. If the change is a bug fix or a non-trivial regression, walk a 3+ step why-chain here (Principle #3).

## Predicted change

Quantitative prediction filled in BEFORE the experiment runs:

- Suite margin: <current> → <predicted>, expected delta: <±N>
- Per-fixture: which fixtures are predicted to move, and how much
- Wall time: expected change (especially if a phase is added or removed)
- Oracle findings: which oracle's findings are predicted to drop

## Diff plan

What files will change, why each is necessary. If the diff exceeds the minimum needed to falsify the hypothesis, justify the surplus or cut it (Principle #1).

## Principles check

| # | Principle | Status | Evidence |
|---|---|---|---|
| 1 | No overengineering | ✅/⚠️/❌ | … |
| 2 | No guesswork | ✅/⚠️/❌ | … |
| 3 | No workaround | ✅/⚠️/❌ | … |
| 4 | Worldclass production-ready | (filled after run) | … |
| 5 | Best practice | (filled after run) | … |

## Actual change

Filled AFTER the benchmark re-runs. Raw numbers, no interpretation.

## Lessons

What we learned, what surprised us, what to feed forward into the next hypothesis. This is where interpretation lives.

## Decision

ACCEPT (ship, freeze new baseline) | REVERT (keep iteration file, don't ship) | DEFER (block on something).
```

---

## Section 2 — RUN

**Branch** (not strictly required, but cleanest):

```bash
git checkout -b iter/NNNN-<slug>
```

**Apply the change.** One or more commits on this branch. Each commit message is a sentence; keep them small enough that a reviewer can read them top-to-bottom.

**Cross-check non-trivial design choices with codex** (per memory: `feedback_codex_cross_check.md`). Send your own analysis first, ask for pushback. Synthesize. Don't outsource the thinking.

**Choose run scope:**

- **Subset re-run** (1-4 fixtures) for a narrow change targeted at known-affected fixtures. Cost: 30 min — 2 hr.
- **Full-suite re-run** (9 fixtures) before declaring SHIPPED. Cost: 4-6 hr.

Subset is for falsification; full suite is for ship gate. Don't ship on subset alone.

```bash
# Subset
bash benchmark/auto-resolve/scripts/run-suite.sh F3-backend-contract-risk F6-dep-audit-native-module --label iter-NNNN
# Full
bash benchmark/auto-resolve/scripts/run-suite.sh --label iter-NNNN
```

**While it runs**, the iteration file's `Status` is `RUNNING`. Don't start a second iteration in parallel — one hypothesis at a time keeps the signal clean.

---

## Section 3 — ANALYZE

**Read the report**: `benchmark/auto-resolve/results/<run-id>/report.md`.

**Fill in `Actual change`** in the iteration file. Required:

- Suite margin before vs after
- Each fixture's variant/bare/margin (the report's table — copy it verbatim)
- Each affected fixture's axis breakdown (Spec/Constraint/Scope/Quality) from `judge.json`
- Oracle findings for each affected fixture (`oracle-test-fidelity.json`, `oracle-scope-tier-a.json`, `oracle-scope-tier-b.json`)
- Wall time delta (variant total minutes)

**Compare to `Predicted change`**:

- Within prediction → mechanism understood. Move to Decision.
- Better than prediction → suspicious. Did something unexpected fire? Did this iteration accidentally fix something else? Trace it before shipping.
- Worse than prediction → mechanism wrong. The hypothesis is refuted. Move to REVERT unless the partial signal points at a refined hypothesis worth a second iteration.

**Fill in `Lessons`.** This is the institutional memory. Even a REVERTED iteration leaves a useful lesson if `Lessons` is honest.

**Re-check Principles 4 and 5** (filled after run, not before):

- Principle #4: zero variant CRITICAL + zero HIGH `design.*`/`security.*` findings on any fixture. Check `judge.json` per fixture.
- Principle #5: zero variant MEDIUM `design.unidiomatic-pattern` findings. Same source.

---

## Section 4 — SHIP-OR-REVERT

**Decision rules:**

- All five principles ✅ AND suite margin not regressed AND no per-fixture margin worse than −5 → **ACCEPT** (ship).
- Any ❌ in Principles → **REVERT** (drop the branch, keep the iteration file with verdict).
- ⚠️ in any principle → **escalate** to user review. Don't auto-ship.
- Subset run only, even with all-✅ → **DEFER** until the full suite confirms. Update Status to RUNNING and run the full suite.

**On ACCEPT:**

```bash
# 1. Merge or rebase iter branch into the working branch
git checkout benchmark/<your-branch>
git merge --ff-only iter/NNNN-<slug>  # or rebase

# 2. Freeze the new baseline
cp benchmark/auto-resolve/results/<run-id>/summary.json \
   autoresearch/baselines/<label>.json

# 3. Append a one-line entry to DECISIONS.md
echo "NNNN | ACCEPT | <one-line description> | iterations/NNNN-<slug>.md" \
  >> autoresearch/DECISIONS.md

# 4. Mark the iteration file Status: SHIPPED, fill in Decided date.

# 5. Remove the item from "Next hypotheses (ordered)" in README.md.
#    If new hypotheses surfaced from Lessons, append them.
```

**On REVERT:**

```bash
# 1. Discard the branch (or keep it as a record; not merged)
git branch -D iter/NNNN-<slug>  # optional

# 2. Append a one-line entry to DECISIONS.md
echo "NNNN | REVERT | <one-line: what was tried, why it didn't work> | iterations/NNNN-<slug>.md" \
  >> autoresearch/DECISIONS.md

# 3. Mark the iteration file Status: REVERTED, fill in Decided date.

# 4. The hypothesis stays out of "Next hypotheses" UNLESS the Lessons
#    section names a refinement worth retrying. If so, write the
#    refined hypothesis as a new entry at the appropriate priority.
```

**On DEFER (waiting for full suite):**

- Iteration Status remains RUNNING. Re-enter Section 2 with the full-suite scope. The Predicted change does not get rewritten — predictions are made once.

---

## Anti-patterns to refuse

- **Re-running until the answer pleases.** Run once. If the result is suspicious (huge gain or huge loss with no clean mechanism), file a new iteration to investigate, don't re-run silently.
- **Renaming a REVERT to ACCEPT post-hoc** because you decided you like the change anyway. The iteration log is append-only history; reflective lying corrupts the institutional memory.
- **Bundling two hypotheses into one iteration** to "save a benchmark run." You will not be able to attribute the result. Each hypothesis gets its own iteration even if their changes are landed in the same commit.
- **Skipping the principles table** because the change feels obvious. The principles table is the cheapest insurance you have against drift.
