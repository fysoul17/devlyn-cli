---
iter: "0029"
title: "Redesign Phase 1 — kernel extraction + adapter contract (B-prime per Codex 2026-04-30)"
status: SHIPPED 2026-04-30 (commit 7ecc0e6)
type: structural — interface relocation, no behavior change
shipped_commit: 7ecc0e6
date: 2026-04-30
mission: 1
---

# iter-0029 — kernel + adapter contract

## Why this iter exists (PRINCIPLES.md pre-flight 0)

The 2-skill redesign locked 2026-04-30 (NORTH-STAR.md "Product surface" + memory `project_2_skill_harness_redesign_2026_04_30.md`) ships in 5 phases. Phase 1 = kernel extraction. Per Codex deep R0 (session `019dde77`), scope is **B-prime: kernel + adapter contract, NO prompt rewrite**.

This is structural prep — moves an existing mechanism into `_shared/` and ships the LLM-agnostic decoupler (schema + per-model adapters) before greenfield SKILL.md work in iter-0031. Reversing Phase 1/2 forces new SKILL.md to bind to old paths.

## Mission 1 service (PRINCIPLES.md #7)

Mission 1 hard NOs untouched. No worktree, no parallel, no team coordination beyond pipeline.state.json. Single-task L1 surface only.

## Hypothesis

**Structural hypothesis**: Relocating `spec-verify-check.py` to `config/skills/_shared/` and shipping `expected.schema.json` + 3 adapter files does NOT regress current `/devlyn:auto-resolve` behavior. All call sites remain functional via path update. Lint passes.

**Falsifiable prediction**:
1. `bash scripts/lint-skills.sh` passes post-mirror.
2. `python3 config/skills/_shared/spec-verify-check.py --check benchmark/auto-resolve/fixtures/F1-cli-trivial-flag/spec.md` returns same exit code as the same script at the old path on the same input.
3. No grep hit for the old path `devlyn:auto-resolve/scripts/spec-verify-check.py` remains in any tracked file (10 call sites updated).

If any prediction fails → revert before commit.

## Scope (B-prime locked per Codex 2026-04-30 R0)

### Ships
1. **`config/skills/_shared/expected.schema.json`** — JSON Schema for `spec.expected.json` (load-bearing LLM-agnostic decoupler). Captures: `verification_commands` array (cmd / exit_code / stdout_contains / stdout_not_contains), `forbidden_patterns` array (pattern / description / files / severity), `required_files`, `forbidden_files`, `max_deps_added`. Sourced from existing `benchmark/auto-resolve/fixtures/SCHEMA.md`.
2. **Move** `config/skills/devlyn:auto-resolve/scripts/spec-verify-check.py` → `config/skills/_shared/spec-verify-check.py`. Behavior unchanged.
3. **Update 10 call sites** for the new path.
4. **`config/skills/_shared/adapters/README.md`** — adapter contract: per-engine delta header injected before canonical phase prompt body. Format rules + when to add a new adapter + what NOT to put in adapter.
5. **`config/skills/_shared/adapters/opus-4-7.md`** — small delta header per Anthropic Opus 4.7 official prompt-engineering guide.
6. **`config/skills/_shared/adapters/gpt-5-5.md`** — small delta header per OpenAI GPT-5.5 official prompt-engineering guide.

### Explicitly NOT in scope (defer per Codex)
- ❌ NO `forbidden-pattern-check.py` consolidation (does not exist post iter-0028 revert).
- ❌ NO `scope-check.py` consolidation (does not exist as a standalone yet).
- ❌ NO `complexity-classifier.py` (Phase 2 work — `/devlyn:resolve` PLAN branching).
- ❌ NO `browser-runner.sh` extraction (current browser path still embedded in `/devlyn:browser-validate`; bigger than Phase 1 needs).
- ❌ NO phase prompt content rewrite (CRITIC self-filter + iter-history annotation cleanup deferred to iter-0031 greenfield rewrite).
- ❌ NO new SKILL.md (Phase 2 work).

## Acceptance gate (pre-registered)

All four must pass before commit:
1. `bash scripts/lint-skills.sh` exit 0.
2. Smoke: `python3 config/skills/_shared/spec-verify-check.py --check benchmark/auto-resolve/fixtures/F1-cli-trivial-flag/spec.md` exit 0 AND emits the expected `.devlyn/spec-verify.json` shape.
3. `grep -rn 'devlyn:auto-resolve/scripts/spec-verify-check' .` returns 0 hits in tracked files (excluding `benchmark/auto-resolve/results/` historical archives).
4. Mirror parity: `diff -q config/skills/_shared/spec-verify-check.py .claude/skills/_shared/spec-verify-check.py` silent (no diff).

## Codex pair-review

R0 (session `019dde77`, 2026-04-30) verdict: **B-prime confirmed**. Critical correction: 3 of 4 worktrees were dirty — separate triage. Adapter shape = β with γ-style runtime header injection (canonical body + per-engine delta).

Convergence reached single-round. R-final triggered only if smoke fails.

## Deliverable execution order

1. Create `_shared/expected.schema.json` (NEW, load-bearing).
2. `git mv` spec-verify-check.py to new path.
3. Edit each call site (SKILL.md, references, lint script).
4. Create `_shared/adapters/` folder + 3 files.
5. Run `node bin/devlyn.js -y` to mirror to `.claude/skills/`.
6. Run acceptance gate checks.
7. Commit if all pass.
