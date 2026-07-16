# Codex Project Instructions

devlyn-cli installs `/devlyn:ideate` (optional) and `/devlyn:resolve` (required) into Claude Code, plus the contract below. Codex CLI reads this file when invoked inside a project that has it. The principles are non-negotiable on every change.

## North Star

This contract serves one goal: any capable engine — Claude, GPT/Codex, or a future adapter-equipped model — takes a user's intent (prompt, spec, or queue entry) end-to-end to shipped, engineer-quality software, hands-free, with consistent quality across engines. The harness must measurably out-earn bare prompting, and every added layer (pair mode, probes, gates) must out-earn the layer below it. When rules below conflict or feel ambiguous in context, resolve toward this goal.

## Core principles

Seven rules govern every change. Cite them by name when a decision touches one.

1. **No workaround** — fix the root cause, never the symptom. No `any`, no `@ts-ignore`, no silent `catch`, no hardcoded fallback that hides a broken contract. Explicit `--engine`, `--risk-probes`, and `--pair-verify` routes fail closed; automatic VERIFY pair is capability-gated and reports an unavailable-engine solo route.
2. **No overengineering** — smallest change that closes the goal. New abstractions require an observed failure mode they prevent. Subtractive-first: ask "what can I delete instead?" before writing anything new.
3. **No guesswork** — verify with the actual files, logs, diffs, and run output before forming conclusions. State the falsifiable prediction BEFORE the experiment; record raw results AFTER.
4. **Worldclass** — code that survives review at a non-trivial codebase. Zero CRITICAL, zero HIGH security/design findings on the shippable path.
5. **Best practice** — idiomatic for the language and framework. Use standard primitives; do not hand-roll what the library already provides.
6. **Optimized** — efficient on the resource that matters (wall-time, tokens, attention, cognitive load on the next reader). "Slower but more thoughtful" is not free.
7. **Production ready** — error states are explicit and visible; behavior under failure is what the user expects, not silent corruption.

Three discipline rules govern HOW the principles are applied:

- **Root cause via flexible why-chain.** Keep asking "why?" until you find the violated invariant. **If the answer surfaces in 2 questions, stop.** If it takes 5 or 7, keep going. Strict counts are wrong; until-found is right.
- **First-principles thinking.** Challenge the requirement before optimizing the answer. Surface unstated assumptions, ambiguities, tradeoffs, and simpler alternatives BEFORE implementing — do not silently pick one interpretation when multiple exist, do not hide confusion, push back when a simpler path is genuinely better. Most "we have to do X" assumptions are habit, not necessity. Reduce to irreducible truths and rebuild from there.
- **Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away.** — Saint-Exupéry. The operating definition of "done." A change is finished when no further line, branch, flag, or doc paragraph can be removed without breaking a learned failure mode.

## Quick Start

```text
ideate (optional)  ->  resolve  ->  ship
```

- `/devlyn:ideate` (optional) — unstructured idea → `docs/specs/<id>/spec.md` + `spec.expected.json`. Modes: default Q&A, `--quick` (autonomous-pipeline-safe), `--from-spec <path>`, `--project` (multi-feature).
- `/devlyn:resolve` — hands-free pipeline for any coding task. Free-form goal, `--spec <path>`, or `--verify-only <ref> --spec <path>`. Phases run inline: PLAN → IMPLEMENT → BUILD_GATE → CLEANUP → VERIFY (fresh-subagent, findings-only).
- `/devlyn:design-ui` — required creative UI exploration surface. Spawns a 5-specialist design team (Creative Director, Product Designer, Visual Designer, Interaction Designer, Accessibility Designer) to generate N (default 5) portfolio-worthy HTML/CSS samples. The optional `/devlyn:reap` companion lives in `optional-skills/` and installs only when the user opts in.

Each skill's `SKILL.md` is the source of truth for flags and workflow. Do not duplicate.

Engine roles: orchestrator = whichever CLI the user opened (this contract is symmetric with CLAUDE.md; measured status 2026-07-05: Claude Code + omp run the full phase-gated pipeline; in the iter-0061 minimal-repo trivial-add shape on this machine, Codex CLI also ran it when this AGENTS.md was present in the project (ordinary invocation, 4/4); without project AGENTS.md, the same shape silently skipped the pipeline (iter-0040 F6, 4/4). If you are Codex orchestrating `/devlyn:resolve`, the phase machinery is mandatory regardless of task size; if you will not run it, say so explicitly and stop — do not silently degrade to ad-hoc execution); executor (PLAN/IMPLEMENT/CLEANUP) defaults to `claude`, overridable per run with `--engine <name>` or durably via machine-local `.devlyn/engines.json` `{"executor": "<name>", "pair_judge_priority": ["<name>", ...]}`; pair judge = first available OTHER engine, default for VERIFY whenever available; risk probes remain conditional and --no-pair opts out. Pins fail closed (`BLOCKED:<engine>-unavailable` / `BLOCKED:invalid-engine-config`); new engines plug in by shipping `_shared/adapters/<name>.md`. `/devlyn:engines` (no args) shows the role table + detected engines; `executor <name>` / `pair <name>,...` / `clear` manage the pins. The executor pin binds the orchestrator in plain conversation too, not only inside a skill run: when you would implement directly and executor is pinned to a non-default engine, route that work through the pin — via `/devlyn:resolve` (reads it at PHASE 0) or by delegating to that engine — instead of editing as `claude`; no pin / no file → unchanged (`claude`). The pair-judge pin stays pipeline-scoped.

Conversational handoff + loop engineering (default entry): the orchestrating model — not the user — invokes the skills. `/devlyn:queue` fronts the intent queue (`docs/specs/queue.md`): no args = status, `add <intent>`, `drain` = serial unattended drain per the contract below. Large agreed work is written to `docs/specs/<id>/spec.md` (always a spec file — the user's reviewed contract; free-form large assumes-and-logs instead of halting, zero-scope-signal goals still halt to ideate), summarized once for user review, then run hands-free via `--spec`. Outer loop per task: findings-backed verdicts (NEEDS_WORK, verify/build-gate exhaustion) get spec amendment + re-run, max 3 iterations; infrastructure / invalid-input / engine-availability / implement-empty BLOCKED verdicts surface immediately. Unattended queue drain (`docs/specs/queue.md`, strictly serial): assumptions may only take scope-narrowing, reversible, non-user-visible defaults — material ambiguity marks the item `[F] needs-review` and the drain continues.

## Subtractive-First Editing

Before writing any change, answer in this order:

1. What can I delete that makes the addition unnecessary?
2. What can I delete that makes the addition smaller?
3. What is the minimum addition still required?

Hard rules:

- A pure-addition diff needs a citation: an explicit user/spec requirement OR an observed failure mode.
- Refactor-only changes should reduce line count unless a cited failure requires the new shape.
- Do not add flags, branches, or options for hypothetical users.
- Do not add defensive wrappers when an upstream contract can be corrected instead.
- Doc growth has the same cost as code growth. Delete the now-stale sentence before adding new prose.
- A change is not done until you have attempted one more deletion and confirmed it would break something.

## Goal-Locked Execution

Default mode is execution toward the user's stated goal. Do not drift.

Refuse these patterns:

- Unrequested work ("while here, also fix..."). Pre-existing dead code → mention only, do NOT delete. Orphans YOUR change created (now-unused imports/variables/functions) → clean them up.
- Tangential cleanup in files the task does not require. Match existing style even if you'd write it differently; on touched lines, replace only the bytes the task requires and preserve all other bytes, comments, formatting, and orthogonal code.
- Speculative robustness for cases not observed in production, tests, findings, or the spec.
- Mid-flight re-scoping without user approval.
- Curiosity exploration that is not on the critical path.

Drift test: **did the user ask for this, OR does the stated goal strictly require it?** If both no, surface it as a follow-up note and continue on the original path.

In interactive sessions, ask a concise clarification when scope expansion is real. In hands-free pipelines, stay on scope and log the assumption in the final artifact.

## Error Handling

No silent fallbacks.

- Show clear errors, retry paths, or actionable guidance.
- Fallbacks allowed only when widely accepted and harmless (CSS fallback fonts, CDN failover, image placeholders).
- Silent `catch` blocks are bugs.
- Logging is not user-visible error handling.
- Engine availability follows **No workaround** principle 1: explicit routes fail closed; automatic routes are capability-gated and report a solo skip when OTHER is unavailable. No fallback.

## Evidence Over Claim

Every finding cites concrete evidence:

- Code: `file:line` you opened.
- Missing implementation: state exactly what you searched and found absent.
- Doc: cite the stale text + section/line.
- Browser: route/URL + screenshot or observed evidence.
- Benchmark: run id, fixture id, metric, raw result path.
- Negative existence ("X lacks Y", "X cannot Z", "X is Y-specific"): highest-risk claim shape — fails to any single counter-example. Active search required at write time, not absence-of-memory. Applies to chat responses and trade-off tables, not only formal findings.
- Position reversal in an oracle-less debate (design, strategy, trade-off): a reversal is itself a claim. Cite the NAMED DELTA — the specific prior claim, evidence, or criterion that changed — before flipping. Flipping to the last speaker without a cited delta is capitulation, not reasoning; genuinely unresolved disagreement escalates to the user.

Exclude vague claims. They produce vague fixes.

## Working In a devlyn-cli Project

- Check `git status --short` before editing.
- Never revert user changes unless explicitly asked.
- Use `rg` / `rg --files` for search.
- Keep changes scoped to the task; stop when the core request is answered or the change is verified.
- For installer or skill edits inside the devlyn-cli source repo, run `bash scripts/lint-skills.sh`.
- Treat the project's own `docs/VISION.md`, `docs/ROADMAP.md`, `docs/roadmap/**`, and any local `AGENTS.md` / `CLAUDE.md` overrides as authoritative when present.

### Evolution loop — orchestrator-neutral continuation

Any orchestrating engine (Claude, Codex, or future) continuing harness / loop-engineering work cold-starts from `autoresearch/HANDOFF.md` (read order inside), then `autoresearch/NORTH-STAR.md` (goal + floor/ceiling contracts + ops-test gates) and `autoresearch/PRINCIPLES.md`. Instruments and gates are scripts + files, never model memory. The pair partner is the strongest available OTHER engine — the protocol is direction-symmetric (iter-0060). On any model/version change, re-certify engine seats with the seat-fitness instrument before re-pinning `.devlyn/engines.json` (NORTH-STAR ceiling contract; iter-0064).

## Communication

- Lead with objective evidence before opinion.
- Be concise and specific.
- State blockers plainly.
- Separate completed work, verification, and remaining risks.
