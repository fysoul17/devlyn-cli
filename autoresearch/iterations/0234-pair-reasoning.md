# 0234 — Pair reasoning against the shipped 4.2.0

**Status:** FROZEN 2026-10-07. Apparatus built by Codex gpt-6-sol from root's contracts (`0234-apparatus-contract.md`, `0234-apparatus-fix1-contract.md`); reviewed by a parallel Claude review workflow (findings adversarially verified) and Astra freeze rounds a1 (REVISE) → a2 (REVISE) → a3 (REVISE) → a4 (FREEZE). Root fixed the treatment's peer commands (a1: the wrapper's file transport refused `resume`; separate per-turn files under `.devlyn/pair/`; 540 s inner deadlines) and the last accounting/diagnostic items (a2–a3). Any later change is a dated addendum.

## 1. Owner message (2026-10-07, verbatim)

> 그리고 추가적으로, 예전에 우리 하네스 테스트 하기 위해서 이것저것 만들어서 측정하고 했는데, 그걸로 측정하면 안되려나? 그래서 현재 하네스가 이전에 비해서 어떤지, 그리고 각 bare solo pair 가 어떤지. pair는 없다면 어떻게 해야 pair 로 할수 있게 만들지 등. astra ultra와 깊게 논의해서 방향을 가지고 진행하고 개선해봐.

Follow-up: shorten the schedule while keeping quality ("오매 줄일수 있는 방법은 없어? 퀄리티는 유지하고"; "응 그렇게 진행해줘").

## 2. Design record

Root and Astra (gpt-6-astra, ultra) wrote independent positions, then converged in one exchange (`.devlyn/bundle/root-pair-p1-position.md`, `pair-p1-astra.out.md`, `pair-p2-prompt.md`, `pair-p2-astra.out.md` in the retained continuation checkout).

- **Old instruments.** Lane A and the resolve-based Lane C runners cannot run 4.2.0; their fixtures can, after normalization. 0233's apparatus is the base. Lane B measures instruction text only; Lane D and the 0113 meter need substantial rework and are not used here.
- **4.2.0 vs before** is answered first from existing data: 0232's A/F beside 0233's A/B on D3/D4, by configuration, under the sensitivity convention in §8. A fresh B/F bridge runs only when a claim we intend to publish needs it (Astra withdrew the unconditional bridge; deciding criterion: an unresolved comparison must change a live decision or a published claim).
- **bare / solo / pair.** Bare is the pinned native CLI without devlyn (A). Solo is the installed product with no mandated peer (B; spontaneous consultations are counted and reported, so B is not an enforced one-engine arm). Pair is that product plus reciprocal deliberation in which both engines shape decisions and the artifact.
- **Prior evidence.** No study isolated the owner's collaboration treatment. May's F16/F23/F25 pair gate (+21/+31/+24 over solo, wall 1.28–2.25×) supports executable counterexamples before implementation as a plausible mechanism, but those are whole-treatment rubric scores including VERIFY pairing, not isolated effects. 0184's repair gain came from a fresh same-engine review; 0229 showed complementary detections on fixed sources; 0232's rung I (one late cross-engine review) raised cost and failed on quality.
- **Mechanism.** Probes inside reciprocal dialogue, three peer turns at most: independent positions with one to three executable counterexamples quoting their request clause; reciprocal development; awaited closure on the submitted source. Disagreement is settled by running the check or citing source. H applies the identical protocol with a same-engine peer, so P−H separates engine diversity from added deliberation.
- **Activation.** An interaction trigger, not C's resource trigger: correctness depends on the order of multiple rules, or on shared state across operations. E1/E2 test false activation.
- **Baseline.** S = B (shipped 4.2.0), so the study can start after 0233's development panel. This establishes B+P vs B only: beating B alone does not earn admission over A if B itself has not earned admission (the confirmation gate therefore also tests P/A directly), and it says nothing about C. C+P is a possible later experiment, not an automatic rung.

## 3. Question

On tasks where the shipped 4.2.0 still fails, does the pair method (P) improve completion and quality without raising wall, input or output per success, and does any gain come from the second engine rather than from added deliberation (H)?

## 4. Arms

| Arm | Treatment | Commit |
|---|---|---|
| A | bare: no devlyn | — |
| B | 4.2.0 | `dd4957775337e597f39838fa73acd5c7ec4a5699` |
| H | B + pair pointer + `_shared/pair.md`, same-engine peer | `335d27130c270e9c947558eb2f9c28a528776e32` |
| P | B + pair pointer + `_shared/pair.md`, other-engine peer | `04712dad0e9f2efcc90aa85b7d5add8f76786fa9` |

Pack digests are pinned in `experiments/0234/DESIGN.md`. H and P differ in one sentence (the peer). The pointer:

> - Pair reasoning — before implementing a change where correctness depends on the order of multiple rules, or on preserving shared state across multiple operations, read `_shared/pair.md` in `.claude/skills/` or `.agents/skills/` (project, else `~`). A single local update with ordinary input validation does not by itself qualify.

## 5. Tasks and panels

Pool in frozen order: I0185, F16, F23, F25, F10, F11 (F16/F23/F25 normalized from `benchmark/auto-resolve/fixtures/` with identical, sufficient participant information for every arm; adaptations and hashes in DESIGN.md). Easy: E1, E2. Smoke: S2.

SMOKE 4 (H/P × configurations) → screening 12 (B × pool × configurations) → development (first two eligible tasks per configuration; B/H/P × 1, plus A, fresh except I0185 whose A reuses 0233's development A cells) → confirmation (next two eligible; A/B/P × 2) → easy 8 (E1/E2 × B/P). Eligibility per configuration: the screening cell is product-incomplete or fails an oracle row. Screening never enters sums. Arm order rotates as in 0233; replicate 2 reverses.

## 6. Environment

As 0233: image, CLI pins, routes, local origin, accounting, assessors, watchdogs. Both CLIs' defaults in every cell equal the registered peer routes (Codex gpt-6-astra high; Claude claude-opus-5-5 high). No other model-heavy work runs during measured cells; root holds cells between runs for its own model work and records each hold.

## 7. Decision rule

0232 §6 per configuration and panel. Confirmation P/B and P/A gate with 0233's quality veto (`FAIL` / `PASS` / `UNCONFIRMED` / `NO_HEADROOM`). Outcome per configuration: `P` (confirmation PASS, development P/B not FAIL), `P-unconfirmed`, or none. H/B and P/H are exploratory and never admit anything. Easy is a reported tripwire. Shipping anything needs the owner's decision with Astra.

## 8. 4.2.0 vs 4.1.0 (descriptive, from existing data)

Frozen before inspecting B's totals: on D3/D4, by configuration, with D = p(B,0233) − p(F,0232) and d = p(A,0233) − p(A,0232), the completion ordering counts as robust to observed A drift only if [D − |d|, D + |d|] excludes zero. For each per-success resource k, with R = k(B,0233)/k(F,0232) and g = max of the two A ratios, the ordering is directional only if [R/g, R·g] lies wholly above or below one. Incomplete accounting uses conservative bounds; zero completions get the qualitative treatment; task-level regressions and severe findings are reported separately. These are sensitivity conventions, not confidence intervals. I0185 is descriptive only (its request changed). Disclosure: before this rule was written, root's table script had already shown 0233's first two B cells (D3: claude incomplete, codex complete); Astra proposed the rule without seeing them.

## 9. Predictions (before any 0234 cell)

**Astra (p2):** screening headroom 4–7 of 12; hard-task activation ≥90% of H/P cells; easy false activation 0/4 P cells; owner-exit peer deaths 0; P/B raw cost ratios wall 1.6×, input 2.0×, output 1.7×; H matches or exceeds P's development completions in at least one orientation (p 0.70); no I0185 P development completion (p 0.70); full P admission 0.15 Claude-owner, 0.08 Codex-owner; some defect reduction but at least one per-success inequality failing in development (p 0.80).

**Root:** screening headroom 5 of 12 (F16/F23/F25 mostly solved by current models; I0185 unsolved in both); activation ≥ 10/12 hard H/P cells; easy false activation ≤ 1/4; P/B raw wall 1.5–2.2×, input 1.8–3×; P completes more confirmation cells than B in at least one configuration (p 0.45); P admitted in at least one configuration (p 0.15); P−H completion difference zero in both orientations (p 0.5).

## 10. Honest limits

One development replicate makes P−H fragile; H is absent from confirmation, so a diversity advantage cannot be confirmed. Reused I0185 A carries period confounding. One screening replicate misses intermittent failures. Two confirmation tasks give narrow transfer.
