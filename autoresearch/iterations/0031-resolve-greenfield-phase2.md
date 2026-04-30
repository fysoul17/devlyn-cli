---
iter: "0031"
title: "Redesign Phase 2 — greenfield `/devlyn:resolve` SKILL.md"
status: SHIPPED 2026-04-30 (commit 4d0e04a)
type: greenfield-interface — replaces current /devlyn:resolve (focused-debug) with the locked 2-skill pipeline shape
shipped_commit: 4d0e04a
date: 2026-04-30
mission: 1
---

# iter-0031 — greenfield `/devlyn:resolve`

## Why this iter exists (PRINCIPLES.md pre-flight 0)

The 2-skill redesign locked 2026-04-30 (NORTH-STAR.md "Product surface") collapses 16 user-facing skills to `/devlyn:ideate` + `/devlyn:resolve` + kernel + `/devlyn:reap`. iter-0029 (commit `7ecc0e6`) shipped Phase 1 — kernel extraction (schema + adapter contract). iter-0031 ships Phase 2 — greenfield `/devlyn:resolve` SKILL.md.

Codex R1 (session `019dde5c`, 2026-04-30): **"Greenfield the interface. Do NOT greenfield the learned mechanisms."** Rewrite the SKILL.md surface; reuse `spec-verify-check.py`, build-gate logic, state discipline, archive contract, engine routing.

## Mission 1 service (PRINCIPLES.md #7)

Single-task L1 surface only. No Mission 2 substrate. Hard NOs untouched.

## Hypothesis

**Structural hypothesis**: A greenfield `/devlyn:resolve` SKILL.md based on the locked phase shape (PLAN → IMPLEMENT → BUILD_GATE → CLEANUP → VERIFY-fresh-subagent) with adapter-injected per-engine prompts will:
- Match or beat `/devlyn:auto-resolve` on golden F1-F9 quality (no regression).
- Cleanly absorb the current `/devlyn:resolve` focused-debug use case via complexity-classifier branching.
- Honor every official prompt-engineering guide rule that the current SKILL.md violates (NEVER/MUST density, iter-history annotations, CRITIC self-filter language).

**Falsifiable predictions** (acceptance gate for THIS iter):
1. `bash scripts/lint-skills.sh` exit 0 with new `/devlyn:resolve/SKILL.md` AND `/devlyn:auto-resolve/SKILL.md` both present.
2. `python3 -c "import yaml; yaml.safe_load(open('config/skills/devlyn:resolve/SKILL.md').read().split('---')[1])"` succeeds (frontmatter valid).
3. New SKILL.md ≤ 250 lines (the current `/devlyn:auto-resolve/SKILL.md` is 251; the new one is constrained per GPT-5.5 outcome-first guidance).
4. Zero `NEVER`, `MUST`, `CRITICAL` (uppercase imperative) in canonical phase prompts (per Opus 4.7 official guide).
5. Zero `*(iter-XXXX:` style inline annotations in any new prompt file (the iter-history noise the official guides warn about).
6. New skill mirrors to `.claude/skills/devlyn:resolve/`.

**Quality A/B (DEFERRED to iter-0033)**: bare-vs-L1 categorical reliability A/B (current `/devlyn:auto-resolve` vs new `/devlyn:resolve`) on F1-F9 + shadow S1. THIS iter ships the SKILL.md + smoke checks only. Quality A/B is the cutover gate, not the ship gate for the SKILL.md itself.

## Scope (locked)

### Ships in this commit

1. **`config/skills/devlyn:resolve/SKILL.md`** — greenfield orchestrator. Replaces existing focused-debug content. Modes: free-form goal | `--spec <path>` | `--verify-only <diff>`.
2. **`config/skills/devlyn:resolve/references/phases/`** — 5 phase prompts:
   - `plan.md` — PLAN with complexity-classifier branching
   - `implement.md` — IMPLEMENT (constrained design judgment per Block 3)
   - `build-gate.md` — BUILD_GATE (reuses spec-verify-check.py + structure mechanics)
   - `cleanup.md` — CLEANUP (inline, task-scoped)
   - `verify.md` — VERIFY (fresh subagent, findings-only, optional cross-model)
3. **`config/skills/devlyn:resolve/references/state-schema.md`** — pipeline.state.json shape (NEW reference; auto-resolve has it inline at `references/pipeline-state.md`, the new one is a leaner copy).
4. **`config/skills/devlyn:resolve/references/free-form-mode.md`** — how complexity classifier picks trivial / medium / large branch from a free-form goal.

### Reuses (NOT rewriting)

- `_shared/spec-verify-check.py` (iter-0029 location)
- `_shared/expected.schema.json` (iter-0029)
- `_shared/adapters/*.md` (iter-0029)
- `_shared/codex-monitored.sh`, `_shared/runtime-principles.md`, `_shared/engine-preflight.md`
- `_shared/codex-config.md`, `_shared/pair-plan-schema.md`
- The build-gate detection matrix (referenced from current auto-resolve)
- Engine routing table (current `_shared/engine-routing.md` if it exists, else absorbed inline)

### Leaves untouched (will deprecate later in Phase 4)

- `config/skills/devlyn:auto-resolve/` — entire directory stays. Phase 4 deprecates after A/B confirms new resolve wins.
- All other skills (ideate, preflight, evaluate, etc.) — touched in their own redesign phases.

## Acceptance gate (pre-registered)

All 6 must pass:
1. `bash scripts/lint-skills.sh` exit 0.
2. SKILL.md frontmatter valid YAML.
3. New SKILL.md ≤ 250 lines.
4. `grep -E '^[[:space:]]*(NEVER|MUST|CRITICAL)' config/skills/devlyn:resolve/**/*.md` returns 0 lines (uppercase imperatives confined to safety-only).
5. `grep -nE '\*\(iter-' config/skills/devlyn:resolve/**/*.md` returns 0 lines (no iter-history noise).
6. Mirror parity for new skill: `.claude/skills/devlyn:resolve/` matches `config/skills/devlyn:resolve/`.

## Codex pair-review

R0 verdict from session `019dde5c` (2026-04-30) confirmed Phase 2 = greenfield SKILL.md, mechanisms reused. R-final triggered IF acceptance gate fails OR if a phase prompt violates an official guide rule we missed.

## Deliverable execution order

1. SKILL.md (orchestrator).
2. 5 phase prompts.
3. 2 reference files (state-schema, free-form-mode).
4. Mirror sync.
5. Acceptance gate run.
6. Commit if all pass.
