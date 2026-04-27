# NORTH-STAR — what we are optimizing, in one place

This file is the single source of truth for the project's goal. Every other doc references this one. If a future session is uncertain about scope, contract, or direction, **read this file first** — do not infer from code, do not assume from older docs, and do not hallucinate intent.

Last refined: 2026-04-27 (post-iter-0016 partial readout, after user clarification of the 3-layer performance contract and pair-efficiency invariant).

---

## The goal in one sentence

**The harness composes frontier LLMs into a hands-free pipeline that delivers engineer-quality software for users who do not know context engineering, with each layer of composition justifying its own additional cost over the layer below.**

Two user groups, both first-class:

1. **Single-LLM users** (Opus alone, GPT-5.5 alone, Qwen alone, etc.) — they get the harness solo. The harness must beat their bare LLM **on quality and on efficiency**.
2. **Multi-LLM users** (Claude + Codex installed, or future Claude + Gemini, etc.) — the harness uses pair patterns where they are worth the cost. The pair must beat the same harness running solo on the strongest of the user's available models, **also on quality and on efficiency**.

---

## The 3-layer performance contract

| Layer | Composition | Quality contract | Efficiency contract |
|---|---|---|---|
| **L0 — bare** | Single LLM, no harness, single direct invocation | Baseline | Baseline |
| **L1 — solo harness** | Single LLM + this harness, no pair patterns active | **Materially better than L0** on the four judge axes (Spec / Constraint / Scope / Quality) | **Wall-time and token cost not worse than running L0 enough times to match L1's quality.** Concretely: L1 must beat `bare-best-of-N` baseline (L0 invoked N times, best/median taken), where N is the wall-time ratio. |
| **L2 — pair harness** | 2+ LLMs (Claude + Codex today; profile-neutral so future swaps are possible) with `solo` / `pair_critic` / `pair_consensus` modes per phase | **Materially better than L1** on quality axes — by lifting fixtures L1 ties or loses on, not by re-confirming fixtures L1 already wins | **Pair budget must out-earn `L1-best-of-M`**, where M is the wall-time ratio of L2 to L1. If pair takes 3× the wall-time, the quality gain must beat the gain from running L1 three times. |

The efficiency contract applies equally to L1 and L2. **"Slower but more thoughtful" is not free** — at every layer, the alternative "just run the cheaper layer N more times" must be empirically worse.

---

## Why bare-best-of-N is the right efficiency baseline

User insight (verbatim, 2026-04-27): *"속도, 즉 효율도 좋아야해. 너무 느리면 오히려 bare를 여러번 돌리는게 나을수도 있잖아?"*

Translation: if L1 takes 10× the wall-time of L0, the user could have invoked L0 ten times and selected the best output. That is L1's true competitive baseline, not single-shot L0. Same logic for L2 vs L1.

**Concrete example from iter-0016 partial readout**:

| Fixture | bare wall | variant (L2) wall | wall ratio | quality lift |
|---|---|---|---|---|
| F2 | 156s (DQ) | 1201s (TO) | 7.7× | both fail |
| F4 | 177s (vs=0.75) | 1012s (vs=1.0) | 5.7× | +0.25 verify |
| F5 | 45s (vs=0.8) | 770s (vs=0.8) | 17× | tie |
| F6 | 82s (vs=0.83) | 876s (vs=0.83) | 10× | tie |

F5/F6 — verify-tie at 17× and 10× wall. Could the user have invoked bare 17 times and gotten a better best-of-17? Plausibly yes for F5 (small task, low variance — 17 shots probably exceeds variant's quality). The harness has not shown evidence to the contrary. **The current variant arm is on the wrong side of the efficiency contract for these fixtures.**

This does not refute the pair hypothesis. It refutes "always-on pair" as a default. Pair has to be gated to the phases where the multi-model decision provably out-earns running the cheaper layer more times.

---

## Operational tests

A change ships only if it can answer all of these with concrete numbers:

### L0 → L1 contract (release blocker — single-LLM users are first-class)
1. **Quality (L1 vs L0)**: L1 arm beats L0 (bare) arm by suite-avg margin ≥ +8 (preferred) or ≥ +5 (floor) on the 4-axis judge rubric, across ≥ 7 of 9 fixtures (F8 known-limit excepted), F9 ≥ +5 (novice flow load-bearing).
2. **Efficiency (L1 vs L0)**: `L1-vs-L0-best-of-N` is the economic baseline — N is the wall-time ratio `L1_wall / L0_wall` per fixture. **Dominance rule**: if L1 ties or loses on quality AND wall ratio ≥ 1.0, fail without invoking best-of-N (the cheaper run wins by default). Sampling for best-of-N uses **oracle-best** (judge picks best of N L0 runs) as the conservative benchmark; median is a stability diagnostic, not a contract.
3. **No hard floor violations**: zero L1 disqualifier, zero L1 CRITICAL/HIGH findings, zero L1 watchdog timeouts.

### L1 → L2 contract (release blocker for L2 product surface; L1 must pass first)
4. **L1 must pass its own gates** (1–3) before L2 ships. L2 passing vs L0 while L1 fails is not acceptable — single-LLM users are not allowed to be a degraded second-class experience.
5. **No regression**: L2 must not regress any fixture's margin materially vs L1 (concretely: no fixture L1→L2 delta worse than −3 axes).
6. **Pair lift on high-value fixtures**: L2 must beat L1 by ≥ +5 on **pair-eligible / high-value fixtures**, defined as fixtures where (a) L1 was tied or lost vs L0, OR (b) the spec touches security / scope / spec-compliance regions where pair_critic/consensus would plausibly help. L2 is *not* expected to beat L1 by ≥ +5 on every fixture — the short-circuit policy explicitly aims for L2 ≈ L1 on easy fixtures. Suite-avg flat +5 is the wrong gate for L2.
7. **L2 efficiency**: `L2-vs-L1-best-of-M` is the economic baseline (M = `L2_wall / L1_wall`). Same dominance rule as #2.
8. **Short-circuit discipline**: L2 only fires the second-model audit when first-model fails a deterministic checklist. The checklist itself is encoded as a `coverage.json` artifact emitted by the first model — every checklist ID must carry `pass / fail / na` plus evidence path/command plus touched-file scope confirmation. Findings rows alone (`constraint.* no-issue-found`) are insufficient — too easy to fake. `coverage_failed=true` triggers escalate-to-pair regardless of severity counts.

### Tool-lift vs deliberation-lift (separate signals — must be empirically attributed)
9. iter-0016 partial readout shows F4 (browser=true) as the only fixture where variant clearly beats bare on verify_score. That is **plausibly tool/phase lift** (browser_validate + security-review native skills), not pair-deliberation lift. The pair hypothesis remains **unproven** until iter-0020 separates the two:
   - Tool-lift: deterministic phases (browser_validate, build_gate, security-review native) firing or not.
   - Deliberation-lift: second-model EVAL / CRITIC / JUDGE producing different conclusions than first-model.
10. Pair-policy iter (iter-0020) must instrument both signals separately. If the lift is mostly tool-attached and not deliberation-attached, the pair-mode design space changes (cheaper, more solo-default, deliberation only when tool gates fire ambiguous).

### Model-agnostic axis
11. **De-prioritized** per user direction (2026-04-27). The harness is profile-neutral in vocabulary (phase names + role names: `BUILD`, `EVAL`, `CRITIC`, `JUDGE`; `solo` / `pair_critic` / `pair_consensus`) but does not yet build runtime engine-swap infrastructure. Cross-model fixtures (e.g. Qwen / Gemini / Gemma variant arms) remain a deferred memo. They become relevant only after L1 / L2 contracts are met for the current Claude+Codex pairing.

### Honest claim boundary (Codex R3 + R4 hard pushback)
12. The **contract** in this file requires single-LLM (Opus alone, GPT-5.5 alone) to be first-class. The **measurable product promise** today is Claude-only on the L1 arm — there is no non-Claude orchestrator path yet, so an "L1-codex" arm cannot honestly be measured. Iter-0019 ships `L1-claude` smoke first; `L1-codex` defers until a non-Claude orchestrator exists. The contract stays first-class for both groups; the *measured claim* must not exceed the data.

13. **L2-vs-L1 compression risk** (Codex R4 hard pushback after iter-0016 partial readout). The current evidence is L2 vs L0, not L2 vs L1. iter-0016 gave suite avg margin +11.6 (L2 over L0). If L1 lands at, hypothetically, +9 over L0, then L2's effective lift over L1 is only +2.6 — below the +5 floor for L2 vs L1 in operational test #6 above.

iter-0019 ships an `L1-claude` **smoke** arm on F1+F2+F4+F9 (4 fixtures × 3 arms) — that is enough to read whether L1 is on or above L0 across diverse categories, but not enough for a release-decision claim against the full 9-fixture gate. **Partial L1 data interpretation is allowed** (e.g. "L1-claude beats L0 on F2 by +X / F4 by +Y / etc., directionally consistent with L1 contract"); **release-readiness language is forbidden** until iter-0020 lands a full 9-fixture L0/L1/L2 paid run and shows L2 actually beats L1 by ≥+5 on pair-eligible fixtures with L1 itself meeting all L0-vs-L1 release gates.

Phrase numbers as "L2 beats L0 in partial readout; L1 directionally observed in iter-0019 smoke; L2-vs-L1 unknown for release decision" until iter-0020's 9-fixture run lands.

---

## The pair-vs-solo policy (iter-0020 target — re-numbered after Codex R3)

Per-phase decision-mode taxonomy. Final form is the iter-0019 ship; the table below is the agreed shape after Codex R2 review (2026-04-27).

| Phase | Default mode | Pair-escalation rule (when L2 active) | Short-circuit rule |
|---|---|---|---|
| ROUTE | solo | never | n/a |
| BUILD | solo Codex | never (single model produces code) | n/a |
| BUILD_GATE | solo deterministic | never | n/a |
| EVAL | gated solo | escalate to pair_critic when verify_score < 1.0 OR design.* / constraint.* findings present OR spec ambiguity flag set | skip second model when verify=1.0 AND zero design.* AND zero constraint.* AND no ambiguity flag AND first model met checklist coverage |
| CRITIC | pair_critic | always pair when L2 active, but short-circuit aggressively | skip second model when first model finds 0 CRITICAL/HIGH AND no uncertainty/coverage flags AND checklist coverage met |
| DOCS | solo | never | n/a |
| JUDGE | pair_consensus | always pair when L2 active | never (consensus is the whole point) |
| FINAL_REPORT | solo | never | n/a |

**"Checklist coverage met"**: the first model explicitly evaluated (a) required constraints from the spec, (b) the touched-file scope, and (c) known failure classes for the phase. If any of those is missing from the first-model output, escalate to pair regardless of severity counts. This is a deterministic anti-overconfidence guard — vibe confidence is not allowed to short-circuit pair.

**"Profile-neutral" (Codex R2 verdict)**: the policy lives in text only. Phase names + role names are abstract; the actual `claude` / `codex` invocations stay inline in the SKILL.md PHASE blocks. Runtime engine-swap (an `engine-roles.json` dispatcher) is **explicitly out of scope** for iter-0019 — overengineering since model-agnostic is no longer the North Star. Add when a real cross-vendor user appears.

---

## Iteration-loop pair vs auto-resolve pair

Per Codex R2 (2026-04-27): **same vocabulary, different thresholds**.

- **Iteration-loop pair** (R0 reviews, this kind of cross-model deliberation on harness changes): human-supervised, can tolerate more pair invocations because the cost is amortized over harness improvements that affect every future run. Threshold: pair freely when stakes are above "single-line text edit".
- **Auto-resolve pair** (the L2 product surface): hands-free, every pair call is paid by the user on every run. Threshold: pair only with the gates listed above. Aggressive short-circuit by default.

Both reuse `solo` / `pair_critic` / `pair_consensus` as the policy vocabulary.

---

## What this North Star displaces / supersedes

- `autoresearch/README.md` "What we're optimizing for" section (lines 9–16): superseded by this file. The README will retain a one-line pointer here.
- `benchmark/auto-resolve/BENCHMARK-DESIGN.md` "LLM-upgrade friendly" aspirational line: subsumed under operational test #7 (de-prioritized model-agnostic axis).
- `benchmark/auto-resolve/RUBRIC.md` ship-gate thresholds: still canonical for the rubric + judge mechanics; release-gate numbers stated here (suite avg ≥ +8 preferred / ≥ +5 floor, F9 ≥ +5, 7/9 fixtures, zero variant DQ/CRITICAL/HIGH/timeouts, wall ratio ≤ 5.0 soft ceiling) are the **release-decision** numbers, layered on top of RUBRIC.md's per-arm scoring rules.
- `autoresearch/PRINCIPLES.md` 5 principles (No overengineering / No guesswork / No workaround / Worldclass production-ready / Best practice): unchanged. They are still the **per-iteration** doctrine. This North Star is the **outer goal** they serve.
- Deferred memos (multi-LLM orchestration modes, benchmark cross-mix arms, model-agnostic): remain deferred, with explicit reason — model-agnostic is no longer the North Star, so cross-vendor work is opportunistic, not load-bearing.

---

## Read order for a new session continuing this work

1. **This file** — what we're optimizing.
2. `autoresearch/HANDOFF.md` — current branch state, last shipped iter, in-flight work.
3. `autoresearch/PRINCIPLES.md` — per-iteration doctrine.
4. `autoresearch/DECISIONS.md` — append-only ship/revert log.
5. `benchmark/auto-resolve/RUBRIC.md` — judge rubric + ship gates.
6. `autoresearch/iterations/0017-run-suite-auto-mirror.md` (or whichever is HEAD) — most recent worked example.

If any of those files contradicts this one, **this one wins** until updated. Open a doc-fix iter.
