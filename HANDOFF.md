# HANDOFF

**Read this first if picking up cold.** Updated 2026-05-29. Owner: Terry K.

Two threads live here. **Thread A (Opus 4.8 / α+)** is the active one — the
principle-aligned follow-ups below are ready to execute. **Thread B (Lane B
instruction-sensitivity benchmark)** is paused, preserved at the bottom.

Full narrative for Thread A is in memory: `project_opus48_harness_readiness_2026_05_29.md`
(loaded via MEMORY.md). This file is the actionable "do next" checklist.

---

# THREAD A — Opus 4.8 / α+ (ACTIVE)

## What shipped this session

- **v2.5.4** (`d064e0e`) — adapter files renamed to engine-neutral
  `_shared/adapters/{claude,codex}.md`; prose convention `<engine>.md`. Model
  upgrades no longer touch adapter files. Plus Stage-1 factual patch (identity
  de-version, stale provenance labels, deleted now-false 4.7 rationales).
- **v2.5.5** (`ec6bbed`) — **α+ capability-gating**. Fixes an L1<L0 inversion:
  a Claude-only run on a high-risk/security spec auto-triggered the cross-engine
  risk-probe / VERIFY pair path, required the absent Codex, and fail-closed with
  `BLOCKED:codex-unavailable` (empty diff) — while bare Opus 4.8 solved it.
  Rule: **automatic escalation is an optimization, not a promise; explicit
  escalation is a promise; no-fallback protects promises.** Auto cross-engine
  escalations now gate on OTHER-engine availability (else proceed solo + report);
  explicit `--risk-probes`/`--pair-verify`/`--engine` still BLOCK.
  Runtime-verified end-to-end on 4.8 (codex absent from PATH, no opt-out flags):
  high-risk spec ran all phases solo to a clean PASS.

## Headline findings (do not re-derive)

- 4.8 needs **no harness rewrite**. CLAUDE.md/AGENTS.md principles, schema,
  canonical phase bodies, rubric are model-neutral. Keep them.
- 4.8 bare is strong enough to **saturate** all current CLI-scale fixtures
  (allocation F23=96, money F16/F25=97, security/prototype-pollution F33 bare=92).
  Pair-mode's win-band on single-file CLI tasks has largely closed under 4.8.
- Runtime verification FALSIFIED a doc-only assumption: α+ also needed a CODE
  change in `verify-merge-findings.py`. Lesson: verify prompt-contract changes
  by running them, not by reading the prompt.

## Follow-ups — principle-aligned, ready to execute

### FU-4 (DO FIRST — cleanest): α+ regression test in self_test()
A sacred-principle change (no-fallback scope) shipped without an automated guard.
Add the two α+ cases to `config/skills/_shared/verify-merge-findings.py`'s
`self_test()` (line ~801). Do NOT build a heavy benchmark fixture (that was F33;
dropped as overengineering — it rippled count-assertions).

The function to exercise is `pair_trigger_skip_contract_violation(devlyn, source_verdicts)`.
Two crafted `.devlyn/pipeline.state.json` states (template proven 2026-05-29):
- `pair_verify: false` + `phases.verify.pair_trigger = {eligible:false, reasons:[], skipped_reason:"auto_pair_other_engine_unavailable"}` → expect **None** (accepted; auto-skip allowed).
- `pair_verify: true` + same trigger → expect finding id **`verify-pair-trigger-auto-skip-explicit-conflict`** (explicit route must BLOCK, never skip).
Mirror to `.claude/skills/` + `.agents/skills/`. Then `python3 …/verify-merge-findings.py --self-test` and `bash scripts/lint-skills.sh` (lint Check at ~line 287 runs the self-test).

### FU-1 (RECONSIDER — NOT a README edit): README:186 lint false positive
`bash scripts/lint-skills.sh` flags `README.md:186` "user-facing retired-surface
reference." **This is a FALSE POSITIVE** — line 186 is the legitimate migration
table (retired skills → `/devlyn:resolve`), the one place those names SHOULD
appear. Prior owner already classified `README.md:182,186` as "leave alone."
Do NOT edit README. If you want lint green: fix the **lint check's over-match**
in `scripts/lint-skills.sh` (the retired-surface grep) to exclude a
migration/deprecation table row. Low priority; leaving it is acceptable.

### FU-2 (LOW — contract fix, not a wrapper): sub_verdicts null
`verify-merge-findings.py` `write_state` (line ~789) does
`sub = verify.setdefault("sub_verdicts", {})` then indexes `sub`. If
`phases.verify.sub_verdicts` is pre-seeded `null` (state-schema's documented
per-phase default), setdefault returns None → crash on the next line. Did NOT
manifest on the verified α+ path. Fix UPSTREAM ("delete the line that makes the
bug impossible"): make the schema/orchestrator not pre-seed `null`, or treat a
null as `{}` at the source — not a downstream defensive `or {}`.

## Deferred — pursuing now would VIOLATE principles

- **4.8 pair-mode measurement.** Binding memory (`feedback_pair_measurement_needs_headroom`):
  no pair-mode iter until fixtures show headroom above L1. CLI-scale fixtures
  saturate on 4.8 (confirmed this session). A real measurement needs a harder
  multi-file surface = **Mission-2** territory, which binds nothing during
  Mission 1 (MISSIONS.md). Building that infra now = speculative / overengineering.
  Right strategic question, wrong as a quick follow-up. Leave deferred.

## Constraints for Thread A work

- Subtractive-first applies to docs too — don't bloat CLAUDE.md/SKILL.md.
- Critical-path skill edits must mirror to `.claude/skills/` AND `.agents/skills/`
  (lint Check 6/6a enforce parity). `.claude/skills` is gitignored; `.agents` is tracked.
- Lint must stay green except the FU-1 README false positive.
- Do NOT weaken no-fallback for explicit routes. α+ only gates AUTOMATIC escalation.
- Release pattern: `npm version patch --no-git-tag-version` → commit work →
  `chore: release vX.Y.Z` → `git tag -a vX.Y.Z` → push main + tag (tag triggers
  `.github/workflows/publish.yml` → npm OIDC publish). lint is NOT a release gate.

---

# THREAD B — Lane B instruction-sensitivity benchmark (PAUSED)

Quantifies whether CLAUDE.md/AGENTS.md/runtime-principles/SKILL.md edits shift
LLM behavior. Lane A (`benchmark/auto-resolve/`) measures pair/risk-probe/headroom
and stays FROZEN; Lane B fills the solo-arm gap.

**Status: Day-3 driver rewrite DONE; next step is the USER's.** The `claude -p`
driver was retired (billed as separate API usage, not subscription). The model
under test now runs as an Agent subagent from a clean `claude --bare` session.
`benchmark/instruction-sensitivity/RUNBOOK.md` is the authoritative ops doc
(§A setup → §E judge/score). Scripts on disk: `build-bundle.py`, `prepare-run.py`,
`capture-arm.py` (new driver); judge/score pipeline unchanged. The old
`run-fixture.sh`/`run-compare.sh`/`extract-transcript.py` are the retired driver —
keep for reference, do not extend.

**Resume**: USER starts the clean `claude --bare` session and runs RUNBOOK.md on
B1–B6 + H1a. Full Day-2 narrative (defects fixed, B4-noise retraction,
AskUserQuestion contamination fix, hard-fixture pilot gates, the "ccd8e6c
redundant-for-sonnet" finding) is in git commit `8678b41` + this file's history.

**Lane B constraints**: models claude=`sonnet`, judge=`gpt-5.5` xhigh (user-locked,
no mini); CLAUDE.md↔AGENTS.md drift is intentional (don't sync the files; behavior
rules are synced); `judge.schema.json` is doc-only (not passed to codex); B1–B6 =
regression-sanity tier, H* = lift tier; H2/H3 ceiling-saturated for sonnet (redesign
or retire); H1a/H1b need an ambiguous task word to trigger clarification.
