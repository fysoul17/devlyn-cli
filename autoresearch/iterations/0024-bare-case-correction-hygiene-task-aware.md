---
iter: "0024"
title: "Bare-Case Guardrail correction + task-aware hygiene severity"
status: shipped
type: contract-correction (no model invocations; rewrites a documented harness rule per user direction + Codex review)
shipped_commit: 349818f
date: 2026-04-29
mission: 1
---

# iter-0024 — Bare-Case Guardrail correction + task-aware hygiene severity

## Why this iter exists (PRINCIPLES.md pre-flight 0)

User direction (verbatim Korean): *"기존 bare case가 틀린거라면 그걸 수정해야해. 북극성을 보자고. 유저가 하나부터 끝까지 다 하는게 목적이 아니야. 유저는 계획하고 실행하면 나머지는 처음부터 끝까지 완벽하게 클린업과 문서화, 기술부채 제거 등을 완벽하게 다 해야해."*

Translation: the harness must perfectly handle cleanup, documentation, and tech-debt removal end-to-end, not push them onto the user via standalone manual tools. The original `Bare-Case Guardrail` rule (CLAUDE.md, pre-iter-0024) said *"complex cases may cost more; the bare case may not"*, and that was a stricter constraint than NORTH-STAR.md actually requires. NORTH-STAR.md:48 defines the cost discipline as `bare-best-of-N` — *quality lift must out-earn N times the cheaper layer*, not *zero-regression on bare* — yet the harness rule was enforcing the latter.

Codex independent review (~138k tokens xhigh, 208s) confirmed the user's correction is correct *in part*: the rule was too strong, but "engineer-quality = full-codebase cleanup every run" would re-create the v1.13.0 failure (538-line SKILL.md, 17.1× wall-time on F5 with no quality gain per iter-0018 readout). The honest correction is **task-scoped polish stays in the default; broad cleanup stays a manual standalone**.

**Decision this iter unlocks**: any future hot-path phase or severity change is judged against the corrected guardrail — *measured quality lift beating bare-best-of-N* — not against a zero-regression-on-bare absolute. Without iter-0024, future iters that add real engineer-quality polish would either be blocked by the wrong rule or smuggled past it dishonestly.

## Mission 1 service (PRINCIPLES.md #7)

Serves Mission 1 gate 1 (L1 vs L0 quality) by closing the contract-vs-promise gap: NORTH-STAR.md:34 promises *"engineer-quality software"* and the Bare-Case rule was preventing the harness from delivering it. Mission 1 hard NOs untouched (no worktree, no parallel-fleet, no resource-lease, no run-scoped state migration, no queue metrics, no multi-agent coordination beyond `pipeline.state.json`, no cross-vendor / model-agnostic infrastructure). Codex confirmed Mission 1 hard NOs are not violated — task-scoped polish is single-task, single-worktree, in-scope per MISSIONS.md:48-55.

No model invocations in this iter. Only document + prompt edits.

## Hypothesis (predicted, written before implementation)

H1 (predicted): Rewriting `Bare-Case Guardrail` to remove the absolute zero-regression-on-bare clause and replace with `bare-best-of-N` framing keeps lint Check 12 (CLAUDE.md ↔ runtime-principles.md per-section parity) PASS, because the rule sits *outside* the four marker-wrapped contract sections (subtractive-first / goal-locked / no-workaround / evidence). Confirmed: lint 13/13 PASS.

H2 (predicted): Splitting `hygiene.*` severity into "task-introduced = MEDIUM blocking" vs "pre-existing = LOW non-blocking" inside `phase-2-evaluate.md` lets the fix-loop catch new tech debt automatically (iter-0024 user direction) without absorbing pre-existing cleanup (Codex's task-scoped vs broad distinction). The split uses `git diff <state.base_ref.sha>` as the deterministic boundary — no judgment required. Confirmed by code review; runtime falsification deferred to A-2 measurement iter (iter-0029 candidate).

H3 (predicted): Existing `PASS_WITH_ISSUES` definition (LOW-only findings → terminal, no fix-loop) remains valid and untouched. Task-introduced hygiene now emits MEDIUM, which routes to NEEDS_WORK → fix-loop, exactly the desired engineer-quality behavior. Pre-existing hygiene stays LOW → terminal, exactly the desired bare-case discipline. Confirmed by reading `phase-2-evaluate.md:33` verdict taxonomy + `SKILL.md:154` PASS_WITH_ISSUES branch.

## Method

Three surgical edits, all subtractive-friendly (each replaces a stricter rule with a precise one rather than adding a new layer).

### Edit 1 — `CLAUDE.md` `Bare-Case Guardrail` rewrite

Replaced single-paragraph rule with three-paragraph clarification:
- **Engineer-quality** is a North-Star promise (NORTH-STAR.md:34). Task-scoped tech debt (silent-catch, scope leak, dead code introduced this run, stale touched-doc refs, `any` / `@ts-ignore`) **belongs in EVAL/CRITIC default behavior**, not behind opt-in flags.
- **Broad codebase polishing** (pre-existing dead code, general README sync, refactoring outside touched scope) **stays with standalone manual tools** (`/devlyn:clean`, `/devlyn:update-docs`, `/devlyn:team-resolve`). v1.13.0's failure mode (cost amplification + contract divergence) is acknowledged and avoided.
- **Cost discipline** is enforced by `bare-best-of-N` (NORTH-STAR.md:48), not by a zero-regression-on-bare rule. Trade-off decided per change with measurement.

### Edit 2 — `phase-2-evaluate.md` task-aware hygiene severity

Existing audit bullet had `hygiene.* at LOW` flat. Added a calibration block right below:
- Hygiene is **MEDIUM blocking** when the issue was **introduced by this diff** (import added but unused; dependency added but never imported; function added but uncalled; touched doc with stale reference to renamed symbols).
- Hygiene stays **LOW non-blocking** when the issue is **pre-existing** in the codebase outside the touched scope.
- Decision rule: `git diff <state.base_ref.sha>`. Inside-diff = task-introduced; outside = pre-existing.

### Edit 3 — `findings-schema.md` task-aware hygiene cross-reference

`hygiene.*` description line gains: *"Severity is task-aware (iter-0024): MEDIUM blocking when introduced by this diff, LOW non-blocking when pre-existing. See phase-2-evaluate.md calibration block."*

Mirrored both `phase-2-evaluate.md` and `findings-schema.md` to `.claude/skills/devlyn:auto-resolve/references/`. CLAUDE.md is project-root and not mirrored.

## Findings (what was actually built)

**Files modified (3)**
- `CLAUDE.md` — `Bare-Case Guardrail` section rewritten (single paragraph → three paragraphs).
- `config/skills/devlyn:auto-resolve/references/phases/phase-2-evaluate.md` — `+1` calibration bullet under existing hygiene audit line.
- `config/skills/devlyn:auto-resolve/references/findings-schema.md` — `hygiene.*` line gains task-aware reference.

**Files added**: `autoresearch/iterations/0024-bare-case-correction-hygiene-task-aware.md` (this file).

**Mirror updates (2)**: `phase-2-evaluate.md` + `findings-schema.md` under `.claude/skills/`.

**Smoke**:
- `bash scripts/lint-skills.sh` → all 13 checks PASS.
- Mirror parity (lint Check 6) clean for both modified `references/*.md`.
- iter-0023 ship-gate verification still produces same L1 readout (no behavior regression).

## What this iter unlocks

1. **iter-0025 (B-1 Opus sidecar)**: cross-judge probe on iter-0020 results, no new model BUILD calls. Tests single-judge bias hypothesis. Trust framework now has the corrected severity rule to interpret outcomes against.
2. **iter-0026 (B-3 F9 re-run)**: F9-only run when quota allows. Closes the F9-empty-data hole.
3. **iter-0027 (B-4 paired L0/L1 variance)**: F2/F3/F9 paired runs, N=3-5. Variance becomes interpretable now that axis values are bounded (iter-0023) and the gate definition is honest (iter-0024).
4. **iter-0028 (B-5 `completed:` removal probe)**: F2 single-fixture re-run after dropping `completed:` from DOCS phase output. Scope-axis hypothesis pre-registered in iter-0021.
5. **iter-0029 (A-2 task-scoped polish measurement)**: F1 + F5 modal fixture wall/token + open-hygiene-finding count + scope delta after iter-0024's severity change. Decides whether the corrected guardrail's promise (engineer-quality on bare path) measures honestly.

## Principles check

### Pre-flight 0 — not score-chasing
**Status: ✅ PASS.** Closes a real contract-vs-promise gap surfaced by the user. Output is rule honesty, not score movement.

### 1. No overengineering / Subtractive-first
✅ PASS. Three edits, no new abstractions, no new flags, no new schemas. Each edit replaces a stricter rule with a precise one (severity split is arguably an addition, but the alternative — a new phase or sub-skill delegation — was explicitly rejected on Codex's recommendation; the chosen form re-uses existing EVAL/fix-loop machinery).

### 2. No guesswork
✅ PASS. H1 (lint preserved) verified post-edit. H2 (severity split is implementable via `git diff` boundary, no judgment) verified by code review. H3 (PASS_WITH_ISSUES contract preserved) verified by reading existing files.

### 3. No workaround
✅ PASS. The user's correction is itself an anti-workaround move (debt was hidden by classifying as LOW; now it's surfaced as MEDIUM and fix-loop addresses it). No `try/except`, no silent fallback added.

### 4. Worldclass production-ready
✅ PASS. Post-EVAL invariant preserved (CRITIC findings-only, DOCS doc-only, fix-loop re-routes through EVAL). No new CRITICAL/HIGH risk introduced; old CLAUDE.md cost-protection rule didn't gate quality, only cost.

### 5. Best practice
✅ PASS. Re-uses existing `git diff <state.base_ref.sha>` boundary that the harness already computes per iter-0014. No new diff parsing, no new helpers.

### 6. Layer-cost-justified
⚠️ BORDERLINE. The rule rewrite explicitly accepts that the bare path may cost more on tasks where new tech debt is introduced — this is honest. The mitigation is the `bare-best-of-N` framing (changes must beat the cheaper layer's N-best, not avoid all regression). iter-0029 (A-2 measurement) is the falsifier: F1 + F5 modal wall/token gets remeasured. If the new severity rule increases bare wall-time without quality lift, revert.

### 7. Mission-bound
✅ PASS. Single-task, single-worktree, no Mission 2/3 surface touched. Codex Q4 explicitly verified no Mission 1 hard NO violation.

## Drift check (산으로?)

- **Removes a real user failure?** Yes. The user-stated failure: *"the harness should handle cleanup/docs/tech-debt removal completely, not push them on me."* iter-0024 closes the rule that prevented exactly that, while staying inside Codex's "task-scoped" boundary to avoid v1.13.0's cost trap.
- **Expands scope beyond what was requested?** No. The corrected severity is pinned to `git diff` — the smallest possible boundary that honors the user's correction.
- **Sets up a multi-iter measurement chain?** Yes — the broader B → A roadmap (B-1 sidecar, B-3 F9, B-4 variance, B-5 scope probe, A-2 measurement). iter-0024 is one step in that chain, not a measurement-only step.
- **"While I'm here" cross-mission additions?** None.

## Codex pair-review trail (this iter)

### R0 / vision-architecture round (~117k tokens xhigh, 193s; transcript at `/Users/aipalm/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/78008a93-84ed-4c44-a393-85338f6f2b4c/tool-results/b8fxwo5fd.txt`)

Verdict: destination = **δ (autonomous AI Agent organisation) via ε (PLAN-as-contract spine) + β (shared rule registry)**, NOT γ (auto-resolve calling standalones live). γ rejected because standalone contracts diverge (interactive vs hands-free, code-mutating vs findings-only).

### R1 / bare-case-correction round (~138k tokens xhigh, 208s; transcript at `/Users/aipalm/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/78008a93-84ed-4c44-a393-85338f6f2b4c/tool-results/bfuujh94r.txt`)

Verdict: user correction half-correct. The Bare-Case rule IS too strong (NORTH-STAR.md:34 + :48 prove the tension). The "engineer-quality = full codebase cleanup every run" reading IS wrong (v1.13.0 failure: SKILL.md 538 lines, 17.1× wall on F5 with no quality lift per iter-0018:32, :54). Recommended framing: **task-scoped hands-free polish in default, broad cleanup in manual standalones**. Recommended smallest falsifiable step: hygiene severity split via existing fix-loop, NOT new phase. iter-0024 adopts this verbatim.

### R2 / diff-review (TBD — to run after iter-0024 ship)

Will inspect this file + the three edits. Convergence: confirm task-aware severity rule is implementable per the `git diff` boundary; confirm Bare-Case rewrite preserves NORTH-STAR.md cite accuracy.

## Cumulative lessons

1. **A documented rule can be stricter than the doc it claims to enforce.** Bare-Case Guardrail used "may not cost more" while NORTH-STAR.md said "must beat best-of-N." Both surfaces existed in CLAUDE.md and NORTH-STAR.md respectively; nobody had read them side-by-side before user pushed back.
2. **Codex's "smallest falsifiable iter" framing applied here too.** I would have proposed adding a new POLISH phase. Codex showed the existing EVAL+fix-loop already had the machinery; only the severity classification was wrong. Severity-edit > new-phase.
3. **Task-aware boundary via `git diff` is the cleanest possible split.** No judgment, no LLM calibration, no new abstraction — just the diff the harness already computes for `state.base_ref.sha`. Engineer-quality on the new code; pre-existing left for manual cleanup.
4. **User correction caught Codex's prior under-correction.** Codex in iter-0022's R0 had blessed the existing Bare-Case rule. User's "기존 bare case가 틀린거라면" forced both Codex and me to re-read NORTH-STAR vs CLAUDE.md side-by-side. Pair-review across multiple rounds + user-as-tiebreaker is what catches these.

## Falsification record (in-session smoke)

| Test | Predicted | Observed |
|---|---|---|
| lint Check 12 (CLAUDE.md ↔ runtime-principles.md parity) PASS post Bare-Case rewrite | PASS (rewrite outside marker sections) | PASS ✓ |
| lint Check 6 mirror parity for `phase-2-evaluate.md` | PASS post mirror | PASS ✓ |
| Mirror diff for `findings-schema.md` clean | clean | clean ✓ |
| iter-0023 ship-gate against iter-0020 run produces same L1 readout | unchanged | unchanged ✓ (no behavior regression) |
| All 13 lint checks PASS | PASS | PASS ✓ |

Total: 5 acceptance gates closed in-session. Real provider/model invocations: 0.
