# AutoResearch — Iterative harness improvement loop

A Karpathy-style outer loop for evolving the devlyn-cli harness. We propose a hypothesis, change one thing, measure against the benchmark, accept or revert, log it. Repeat. Skills get smarter; the loop becomes the institutional memory.

This folder is the operating manual and the trail of crumbs. It is not a framework you build once; it is the place future-you (or a future LLM running this loop) reads first.

---

## What we're optimizing for

**Performance = the harness reliably extracts engineer-quality software from the LLM regardless of who is asking or what they are asking.** Concrete bar:

- Someone with no software engineering background hands the harness an unstructured ask. The output reads as if a senior engineer worked on it: scope-disciplined, no silent catches, idiomatic, tests preserved, error states visible.
- The user does not need to know context engineering. The harness handles it.

The benchmark suite (`benchmark/auto-resolve/`) is the measurement instrument. Suite margin (variant − bare) is the primary signal; the four rubric axes (Spec / Constraint / Scope / Quality), oracle findings, and wall time are secondary.

---

## How the loop runs

One iteration = one **falsifiable hypothesis** that may span multiple commits and one or more benchmark runs. The unit is the hypothesis, not the commit.

```
   ┌──────────────────────────────────────────────────────────────┐
   │ 1. PROPOSE   — pick the next hypothesis from "Next" below.   │
   │              Write iterations/NNNN-<slug>.md with the         │
   │              schema in playbooks/iteration-loop.md.           │
   │                                                              │
   │ 2. RUN       — apply the change as one or more commits on a   │
   │              branch. Re-run the benchmark (subset first if    │
   │              the change is narrow; full suite for ship).      │
   │                                                              │
   │ 3. ANALYZE   — fill in the iteration's "Actual" + "Lessons"   │
   │              sections with real data. Oracle findings,        │
   │              axis deltas, fixture-level wins/regressions.     │
   │                                                              │
   │ 4. SHIP/REVERT — decide. Append a one-line entry to           │
   │              DECISIONS.md. If shipped, freeze the new         │
   │              baseline in baselines/. If reverted, leave       │
   │              the iteration file with the verdict.             │
   └──────────────────────────────────────────────────────────────┘
```

Full instructions: `playbooks/iteration-loop.md`.

---

## What we measure

These metrics define "did this hypothesis work?". Stable across iterations.

| Metric | Source | Why it matters |
|---|---|---|
| **Suite margin** (variant − bare avg) | `report.md` | Primary "harness adds value" signal. |
| **Per-fixture margin** | `report.md` | Catches regressions an aggregate would hide. |
| **Axis deltas** (Spec/Constraint/Scope/Quality) | `judge.json` | Where the value lives or where a regression originated. |
| **Disqualifier count** (variant vs bare) | `report.md` + `judge.json` | Hard-floor failures. Variant target = 0. |
| **Oracle findings** (test-fidelity, scope-tier-a, scope-tier-b) | `oracle-*.json` per arm | Deterministic signals less noisy than the judge. |
| **Wall time** (variant total) | `report.md` | Bare-Case Guardrail. A skill change that improves quality but doubles wall time costs something real. |
| **Held-out fixtures** | (future, when we have an overfitting signal) | Anti-overfitting guard. Not built yet — see "Anti-overfitting" below. |

---

## Next hypotheses (ordered)

Active queue. Re-order in place when priorities change. The top item is what the next iteration tackles.

1. **Variant subprocess MCP/config isolation (iteration 0004).** Codex round 3 corrected the iteration 0003 framing: F7 variant likely hangs not on a codex MCP race but on Claude Code itself loading every user-level MCP plugin (pencil, codex-cli, telegram, vercel-plugin, …) at `claude -p` startup. Project policy already says "MCP is not in the loop"; the harness was leaking user MCP into the experiment. Fix: `--strict-mcp-config --mcp-config '{"mcpServers":{}}' --debug-file …` on both arms in `run-fixture.sh`. Pre-drafted in `iterations/0004-mcp-isolation.md`. Predicted: F7 variant transcript becomes non-empty, completion within ~10–15 min, margin recovers per iteration 0002's intent (≥+5).

2. **5-Why operationalization in `phase-1-build.md` quality_bar.** User confirmed 5-Why is widely applied, not narrow. Codex round 2 conceded CLAUDE.md placement (Karpathy #1 expansion) is correct under that usage pattern. One-paragraph edit to CLAUDE.md `Karpathy 4 → Think Before Coding`. Predicted: marginal improvement in non-trivial fixtures (F3-class) where root-cause discipline matters; no measurable change on trivial fixtures.

3. **DOCS phase Job 2 wider verification.** v3.7-final + v3.7-fix-f6f7 confirmed the `verbatim-named files only` narrowing eliminated F6 README scope creep. Verify on a fresh full run with a deliberately ambiguous "update the docs" instruction in a fixture's spec body to confirm the rule holds when the spec text gives the model interpretive room.

4. **Held-out fixture set.** Hold off until a hypothesis improves 3+ fixtures with no intuitive mechanism — that's the overfitting signal. Then add 2-3 fresh fixtures as held-out and re-evaluate. Don't pre-build infrastructure for an unobserved problem.

5. **Adversarial-ask layer.** Currently the benchmark only measures the harness against well-formed specs. The non-engineer-user goal is partly an adversarial-ask story: spec text that asks for a workaround, vague intent, off-topic constraints. F8 is the only fixture currently testing this. Expand later.

(When item 1 ships and the benchmark re-runs cleanly across all 9 fixtures, this list rotates.)

---

## Anti-overfitting

We have nine fixtures. We are not yet held-out-splitting them, by deliberate decision: building the split costs fixture-design work and reduces the optimization surface from 9 to 6-7 before we have evidence we need it.

**Trigger to add a held-out set**: a hypothesis improves 3+ fixtures' margins by ≥+5 each AND has no intuitive mechanism explaining why all three improved together. That is the overfitting signature. At that point, freeze 2-3 fresh fixtures (or rotate existing ones into "held-out") and require the next ship to maintain its wins on the held-out set as well as the optimization set.

Until then, every fixture is fair game and the suite margin is the gate.

---

## Folder layout

```
autoresearch/
├── README.md           — this file (overview, metrics, next-hypotheses queue)
├── PRINCIPLES.md       — five principles + concrete operational tests
├── DECISIONS.md        — append-only one-line log: NNNN | ACCEPT/REVERT | desc | iter file
├── HANDOFF.md          — what the next session needs to know to continue
├── iterations/
│   └── NNNN-<slug>.md  — one file per hypothesis (schema in playbooks/)
├── baselines/
│   └── <label>.json    — frozen `summary.json` from each shipped run
└── playbooks/
    └── iteration-loop.md  — propose / run / analyze / ship-or-revert
```

Files we deliberately did NOT create:
- `METRICS.md` — merged into this README (metrics change at the same frequency as the README itself).
- `BACKLOG.md` — folded into the "Next hypotheses (ordered)" section above (a separate file would drift; an in-place section gets re-edited).
- Four separate playbook files — collapsed into one `iteration-loop.md` (linear access pattern, no cross-file coherence cost worth paying).

These cuts are deliberate per Karpathy "delete before you add"; if a learned failure mode demands one back, add it then.

---

## When to use this folder

- About to change a skill prompt? → propose an iteration first.
- Just saw an unexpected regression in a benchmark run? → log it as a hypothesis-shaped iteration ("Why did F7 score drop? Hypothesis: …").
- Reviewing the last week's work? → `cat DECISIONS.md` is a 30-second scan of trajectory.
- Onboarding (you or an LLM) onto this loop? → read PRINCIPLES.md, then this README, then `playbooks/iteration-loop.md`, then the most recent iteration file as a worked example.
