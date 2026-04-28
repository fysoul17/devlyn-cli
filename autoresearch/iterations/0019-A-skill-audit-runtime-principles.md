# iter-0019.A — SKILL audit: runtime-principles + preflight Round 2 + principle audit overlay

**Status**: SHIPPED (this commit). Code-only iter, no paid suite, lint 11/11 green + Check 12 (new) PASS.
**Date**: 2026-04-28
**Branch**: benchmark/v3.6-ab-20260423-191315

## Why this iter exists (Pre-flight 0)

User halt question 2026-04-28 (Korean verbatim, do NOT paraphrase):

> "지금 우리 북극성과 원리 원칙에 맞는거야? skill 개선하는게 맞는거냐고."
> "auto-resolve가 됐든, ideate가 되었든 ... 북극성을 제대로 바로 세워서 이를 통해서 harness를 하게 하는게 목적인걸로 알고 있는데 ... 우리 skill도 이런게 반영이 되어있나? 이용자가 그런거 잘 모르는 사람이더라도?"
> "preflight 는 그 북극성의 의대대로 클린하게 잘 구현되었는가를 체크하는게 본질이지. codex와의 compenion 으로서 pair 로서 티키타카 하면서 최선의 결과를 검증. 그리고 우리의 원칙대로 잘 되었는가 등"

The previously-staged iter-0019.7 (silent-catch BUILD_GATE helper) BEFORE iter-0019.8 was confirmed as score-chasing per pre-flight 0 (Codex R-halt verdict, 101k tokens, xhigh, 159s). Real-user runs would hit silent no-op without `.devlyn/forbidden-patterns.json` staging — would only move benchmark numbers. **Reordered.**

This iter answers the user's audit question directly: **does the harness enforce North Star + goal-locked + drift prevention + subtractive-first + Codex pair tickitaka on sub-agents even when end-user doesn't know context engineering?** The audit found gaps in 3 areas (Codex pair tickitaka in preflight, principle-evidence findings in preflight, CLAUDE.md rules not propagating to SKILL prompts) and this iter closes all 3. Pre-flight 0 PASS — directly user-failure-removing for the harness contract itself.

## Hypotheses (locked BEFORE the patch)

1. **CLAUDE.md "Subtractive-first / Goal-locked / No-workaround / Evidence" rules propagate to sub-agents** via `_shared/runtime-principles.md` shared file + per-section markers + lint Check 12 wording-parity enforcement. Falsification: lint Check 12 must PASS on contract-block byte-equality between CLAUDE.md and `runtime-principles.md`.
2. **preflight Codex pair becomes multi-round (티키타카) with deterministic short-circuits**, not single-shot critic. Falsification: PHASE 3.5 has 5 deterministic triggers; PHASE 3 emits Synthesis diagnostics block with full lists (not counts) so R2 input is report-only.
3. **principle-evidence findings emit canonical rule_ids only (no fake `tags` field)**, principle attribution lives in `message`/`fix_hint` prose. Falsification: phase-2/phase-3/code-auditor reference `findings-schema.md` rule_ids only.
4. **ideate is correctly NOT a consumer** — planning-layer, CHALLENGE rubric covers analogous concerns, deliberate one-shot Codex critic discipline. Falsification: `ideate/SKILL.md` is unchanged in this iter.

## Mechanism shipped

### New file: `config/skills/_shared/runtime-principles.md` (~120 lines)

Sub-agent runtime contract. Mirrors 4 CLAUDE.md sections (Subtractive-first / Goal-locked / No-workaround / Evidence) inside `<!-- runtime-principles:contract:begin/end -->` block. Each of 4 sections wrapped with `<!-- runtime-principles:section=NAME:begin/end -->` markers (mirrored exactly in CLAUDE.md). Consumption block names consumers (auto-resolve + preflight) and explicit non-consumer (ideate).

### CLAUDE.md changes (+25/-9)

- Added per-section markers around 4 contract sections.
- Added new "Evidence over claim" section (was missing — runtime-principles needed 4 sections; CLAUDE.md only had 3).
- Folded "Documented exception — Codex CLI availability downgrade" subheader into No-workaround section as a "Permitted exceptions" bullet list (subtractive-first compensating cut).

### auto-resolve consumption (+47/-4 across 4 files)

- `SKILL.md` `<harness_principles>`: 3-line summary → 1-line pointer to runtime-principles.md.
- `SKILL.md` PHASE 2.5 fix-loop prompt: inline 4-section operational excerpt (Codex routing).
- `SKILL.md` PHASE 4 DOCS prompt: inline excerpt scoped to DOCS (Goal-locked / Subtractive / Evidence — no No-workaround since DOCS doesn't write code).
- `phase-1-build.md`: added `<runtime_principles>` block after `<principle>` (4-section excerpt). Removed redundant `Fix root causes only — no any/...` line from `<quality_bar>` (compensating cut).
- `phase-2-evaluate.md`: added `<runtime_principles>` block with EVAL-specific patterns mapped to canonical rule_ids only (`scope.out-of-scope-violation`, `types.any-cast-escape`, `correctness.silent-error`); principle attribution in `message`/`fix_hint` prose.
- `phase-3-critic.md`: same shape, CRITIC-specific patterns (`design.unidiomatic-pattern`, `design.duplicate-pattern`, `design.hidden-assumption`).

### preflight changes (+148/-12 across 5 files)

- `SKILL.md` PHASE 3 step 2: deduplicate now records material auditor disagreements (category mismatch, severity boundary cross, any CRITICAL involvement) for PHASE 3.5 trigger 2. Dedup identity has fallback for findings without `(rule_id, file, line)` (uses `(commitment_id, normalized_evidence_locator)`).
- `SKILL.md` PHASE 3 step 5: report-template adds Synthesis diagnostics + Round 2 critique sections (between Findings and Documentation Findings). Header gains `Coverage:` (always present) + `Round 2:` lines.
- `SKILL.md` PHASE 3 step 6: defers user presentation until PHASE 3.5 completes (avoid pre-R2/post-R2 view churn).
- `SKILL.md` **PHASE 3.5 (NEW)**: 5 deterministic triggers (`r2.findings_critical_or_high`, `r2.auditor_disagreement`, `r2.missing_evidence`, `r2.autofix_would_promote_blocker`, `r2.user_explicit`). Engine routes from actual Round 1 engine (not requested — handles silent codex-unavailable downgrade). Input is synthesized report only (no re-audit). 240s wall-budget abort. Single round at runtime; autoresearch-loop developer-invoked preflight is exempt. R2 verdicts: `CONFIRMED` / `REVISED` / `BLOCKED` / `timeout`. PHASE 4 active-set rule consumes post-R2 findings; `RETRACTED` skipped, `BLOCKED` halts `--autofix`.
- `SKILL.md` `--engine auto` code-auditor spawn now optionally inlines `base_ref_sha:` for change-aware principle.subtractive-first-violation firing.
- `SKILL.md` PHASE 4 step 0: presents the final post-R2 report.
- `references/report-template.md`: header, Summary table, Synthesis diagnostics + Round 2 critique sections, finding examples include `[SCOPE_VIOLATION]` + `principle.goal-locked-drift` and `[PRINCIPLE_VIOLATION]` + `principle.unjustified-duplicate-machinery`.
- `references/auditors/code-auditor.md`: `PRINCIPLE_VIOLATION` classification row (fallback only). New "Principles Pass" section with inlined contract excerpt + 6-row rule_id overlay table + decision rule + excluded list (`principle.score-chasing`/`principle.layer-cost-justified` are autoresearch-loop concerns, not runtime). `principle.subtractive-first-violation` conditional on `base_ref_sha`. Output summary now includes SCOPE_VIOLATION + PRINCIPLE_VIOLATION counts; finding examples include `**Rule ID**:` field.
- `references/auditors/browser-auditor.md`: narrow scope — only `principle.no-silent-fallback` and `principle.goal-locked-drift` allowed, screenshot **AND** route evidence required (both, not OR). Other principle.* are code-auditor scope. docs-auditor does NOT emit principle.* at all.
- `references/triage-templates.md`: accepted-divergences shape supports commitment-less findings via `[none] [rule_id]+[locator]`.

### Lint changes (+103/-11)

- **Check 6 expanded**: 7 critical-path files added — phase-1/2/3 prompts + 3 preflight references + `_shared/runtime-principles.md`.
- **NEW Check 12**: CLAUDE.md ↔ runtime-principles.md per-section excerpt parity. 3-layer validation:
  1. **Markers**: each begin/end appears exactly once per file (catches duplicate or missing).
  2. **Topology**: in `runtime-principles.md`, all 4 section blocks live INSIDE the outer `:contract:` block AND in canonical order (`subtractive-first → goal-locked → no-workaround → evidence`). CLAUDE.md placement is free (sections may live in any order).
  3. **Content**: byte-identical content between markers, via `diff` over awk-extracted temp files (preserves trailing newlines that command substitution would strip — Codex Step 5 finding 1).

## Codex companion pair-review log (5 rounds across this iter)

- **Audit Round 1** (132k tokens, xhigh, ~150s): scoped 3 gaps (A: pair tickitaka, B: principle taxonomy, C: CLAUDE.md propagation). Refined Gap A to preflight-only (ideate's one-shot Codex critic is deliberate). Rejected heavy `PRINCIPLE_VIOLATION` category in favor of rule_id overlay.
- **Audit Round 2** (81k tokens, xhigh, ~200s): converged patch shape — RND2 5 triggers + auditor_disagreement materiality rule + Synthesis diagnostics shape; rule_id overlay 6-row table; `_shared/runtime-principles.md` + lint Check 12 (separate from Check 6). Single iter (`iter-0019.A`).
- **Step 1 review** (102k tokens, 198s): 7 edits to runtime-principles.md draft — config-knob threshold restored, "no hardcoded values" wording, false consumption-block claims fixed, separator/lint-doc lines cut, marker split (contract + consumption).
- **Step 2 review × 2** (102k + 45k tokens): HIGH×2 + MEDIUM×2 — fix-loop + DOCS Codex hot paths (added inline excerpts), `DIVERGENT` (preflight category) → canonical auto-resolve rule_ids, `principle.*` "tag" → message/fix_hint prose only (schema has no `tags`), runtime-principles wording soften. Plus phase-1-build.md:44 redundant line cut, phase-2 conditional drop, fix-loop No-workaround wording fix.
- **Step 3 review** (47k tokens, 135s): 7 findings — forward-references gated to atomic commit, R2 critique placement contradiction (Findings → R2 critique → Documentation Findings), user presentation defer, Synthesis diagnostics count→full-list, dedup key fallback, R2 engine = actual Round 1 engine, R2 BLOCKED + RETRACTED Phase 4 interaction.
- **Step 4 review** (64k tokens, ~180s): 6 findings — report-template example fix (SCOPE_VIOLATION + rule_id, not PRINCIPLE_VIOLATION), SCOPE_VIOLATION definition broaden, code-auditor summary + Rule ID field, base_ref_sha orchestrator signal, browser-auditor screenshot AND route, Coverage always-present alignment.
- **Step 5 review** (68k tokens, ~150s): 3 findings — Check 12 byte-compare via diff (command substitution strips newlines), marker topology validation, runtime-principles "verbatim" wording fix.

All Codex findings adopted. Total Codex spend on this iter: ~640k tokens read + ~150k written across 7 rounds, all on `read-only` sandbox + xhigh reasoning.

## Falsification gate results

- **Lint 11/11 PASS** + Check 12 PASS (markers + topology + content byte-equality).
- **Mirror parity Check 6 PASS** post `node bin/devlyn.js -y` (Step 6).
- **No code execution paid run needed** (text-only contract iter — paid runs are reserved for behavior-change iters per pre-flight 0).
- iter-0019.A acceptance is verified by lint, not benchmark spend.

## What this iter unlocks

**iter-0019.8** (real-user contract carrier — `/devlyn:auto-resolve` PHASE 0 emits `.devlyn/spec-verify.json` from spec ## Verification): unblocked. Now that runtime-principles is shared and preflight emits principle.* findings, real-user contract generation can land without changing the audit shape.

**iter-0019.7** (silent-catch BUILD_GATE helper): **deferred to measurement-driven decision after iter-0019.8 lands**. Per Codex R-halt — the right order is iter-0019.8 first to give real users the gate, then measure whether silent-catch persists on real-user paths, then ship 0019.7 only if data demands. Current placement in queue: post-iter-0019.8.

**iter-0020** (cost-aware pair policy + 9-fixture L0/L1/L2 paid run): blocked by iter-0019.8 + measurement of iter-0019.7. iter-0019.A's principle-audit overlay gives iter-0020's coverage.json a richer foundation (rule_id overlay enables principle-coverage tracking).

## Principles 1-6 check

- **Pre-flight 0** ✅ removes user failure (sub-agents not enforcing North Star + drift prevention) — direct, traceable to user halt question.
- **#1 No overengineering** ✅ shared file + per-section markers (cleanest mechanism). Considered alternatives (single contract block, hash parity) and rejected per Codex Step 5 verdict. Markers are minimum mechanism.
- **#2 No guesswork** ✅ 4 hypotheses locked before patch. Each falsified by concrete lint check (Check 12 PASS = parity hypothesis confirmed; marker count per file = topology hypothesis confirmed).
- **#3 No workaround** ✅ root-cause fix at correct layer. Sub-agents inheriting CLAUDE.md rules via shared file = the deepest level the why-chain reaches given CLAUDE.md is session-level not sub-agent-level.
- **#4 Worldclass** ✅ canonical findings schema preserved (no fake `tags`); Codex routing inline excerpt is contract-faithful.
- **#5 Best practice** ✅ standard awk extraction + diff comparison (no custom parser); marker convention is HTML-comment-style (markdown-safe).
- **#6 Layer-cost-justified** ✅ iteration-loop Codex pair (this audit + 7 review rounds) amortized over every future skill-driven run that consumes runtime-principles. Runtime preflight RND2 has 5 deterministic triggers + 240s wall abort + single round at runtime — short-circuit discipline applied.

## Lessons (cumulative)

1. **CLAUDE.md propagation gap was real**: outer-loop developer rules don't reach sub-agents automatically. Shared file + lint parity check is the mechanism. Pattern: every cross-layer rule needs a propagation mechanism + drift detector.
2. **One-shot Codex critic is sometimes deliberate** (ideate CHALLENGE) — multi-round (티키타카) is appropriate at preflight (verification gate) but wrong at planning (cost + trust churn). Codex Round 1 verdict was load-bearing here.
3. **Schema discipline matters**: phase-2/phase-3 initially had `principle.*` "tags" — not in `findings-schema.md`. Codex Step 2 caught it. Lesson: every new finding-emission path must be schema-checked at design time, not after.
4. **Subtractive-first applies to lint code too**: Check 12 hardening (marker topology + diff over temp files) added ~30 lines but caught 3 categories of drift the simpler version missed (trailing newlines, marker duplication, contract-block containment). Pure additions can still be net-positive when each line closes a specific failure mode.
5. **CLAUDE.md is the single source of truth for runtime principles** — runtime-principles.md mirrors it byte-for-byte. Future principle additions go to CLAUDE.md first, then sync via the marker mechanism.
