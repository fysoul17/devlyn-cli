# AutoResearch — Iterative harness improvement loop

A Karpathy-style outer loop for evolving the devlyn-cli harness. We propose a hypothesis, change one thing, measure against the benchmark, accept or revert, log it. Repeat. Skills get smarter; the loop becomes the institutional memory.

This folder is the operating manual and the trail of crumbs. It is not a framework you build once; it is the place future-you (or a future LLM running this loop) reads first.

---

## What we're optimizing for

**See [`NORTH-STAR.md`](NORTH-STAR.md).** That file is canonical and is the first thing a new session should read. The summary kept here is a pointer — when it drifts from `NORTH-STAR.md`, the latter wins.

**One-sentence summary**: the harness composes frontier LLMs into a hands-free pipeline that delivers engineer-quality software for users who do not know context engineering, with each composition layer (L0 bare → L1 solo harness → L2 pair harness) justifying its additional cost over the layer below on **both quality and efficiency**.

**Two first-class user groups**: single-LLM users (Opus alone or GPT-5.5 alone) get L1; multi-LLM users get L2. Both must beat their respective baselines on quality AND wall-time efficiency (concretely: each layer must beat `previous-layer-best-of-N` where N is the wall-time ratio).

The benchmark suite (`benchmark/auto-resolve/`) is the measurement instrument. Suite margin (variant − bare) is the headline; wall-time ratio + per-fixture quality lift + judge-axis deltas (Spec / Constraint / Scope / Quality), oracle findings, and disqualifier counts together form the release-decision signal documented in `NORTH-STAR.md`.

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

**Authoritative copy of the queue lives in [`HANDOFF.md`](HANDOFF.md) "Next iteration QUEUE" — that file is rewritten every iter and the README mirror has historically drifted. When this section disagrees with HANDOFF.md, HANDOFF.md wins.** Snapshot below is the post-iter-0017 + post-North-Star-refinement queue (2026-04-27, after Codex GPT-5.5 R1 + R2 + R3):

1. **iter-0018 — Measurement integrity + report-shape lock.** Finish iter-0016, compile canonical 9-fixture report, inspect F2 timeout / disqualifier patterns. Add `wall_ratio_*` comparison fields to `summary.json`. Diagnostic only — no gate behavior, no prompt retune.
2. **iter-0019 — `L1-claude` smoke arm + comparison schema.** Add `solo_claude` arm to run-suite (Claude alone, no Codex BUILD or CRITIC audit). Smoke fixtures F1+F2+F4+F9. `L1-codex` deferred — Claude is the auto-resolve orchestrator today, no honest L1-codex arm exists yet.
3. **iter-0020 — Pair-vs-solo policy + tool-vs-deliberation attribution.** Per-phase `solo` / `pair_critic` / `pair_consensus` mapping per [`NORTH-STAR.md`](NORTH-STAR.md). Adds wall-time abort + `coverage.json` checklist artifact + critical instrumentation: separate measurement of tool/phase lift (browser_validate, build_gate, security-review native) from model-deliberation lift (second-model EVAL/CRITIC/JUDGE producing different conclusions).
4. **iter-0021 — Dual-judge permanent (`pair_consensus` for JUDGE phase).** Resolves "GPT-only judge is a strategic liability" (Codex R1).
5. **iter-0022 — Cost retune** (only if iter-0020 short-circuits + iter-0019 data show wall ratio still over budget). Otherwise close as "not needed."
6. **Held-out fixture set** (long-deferred). Trigger: 3+ fixtures improve with no intuitive mechanism — overfitting signature.
7. **Adversarial-ask layer** (long-term). Currently only F8 tests adversarial spec text; non-engineer-user goal needs more.

Codex R3 explicit warning: do NOT bundle judge-mechanics + L1 arm + pair policy in the same iter — attribution becomes muddy. The 0018 → 0019 → 0020 → 0021 sequence above keeps measurement and behavior changes separate.

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
