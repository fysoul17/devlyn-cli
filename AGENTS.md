# Codex Project Instructions

devlyn-cli installs `/devlyn:ideate` (optional) and `/devlyn:resolve` (required) into Claude Code, plus the contract below. Codex CLI reads this file when invoked inside a project that has it. The principles are non-negotiable on every change.

## Core principles

Seven rules govern every change. Cite them by name when a decision touches one.

1. **No workaround** — fix the root cause, never the symptom. No `any`, no `@ts-ignore`, no silent `catch`, no hardcoded fallback that hides a broken contract.
2. **No overengineering** — smallest change that closes the goal. New abstractions require an observed failure mode they prevent. Subtractive-first: ask "what can I delete instead?" before writing anything new.
3. **No guesswork** — verify with the actual files, logs, diffs, and run output before forming conclusions. State the falsifiable prediction BEFORE the experiment; record raw results AFTER.
4. **Worldclass** — code that survives review at a non-trivial codebase. Zero CRITICAL, zero HIGH security/design findings on the shippable path.
5. **Best practice** — idiomatic for the language and framework. Use standard primitives; do not hand-roll what the library already provides.
6. **Optimized** — efficient on the resource that matters (wall-time, tokens, attention, cognitive load on the next reader). "Slower but more thoughtful" is not free.
7. **Production ready** — error states are explicit and visible; behavior under failure is what the user expects, not silent corruption.

Three discipline rules govern HOW the principles are applied:

- **Root cause via flexible why-chain.** Keep asking "why?" until you find the violated invariant. **If the answer surfaces in 2 questions, stop.** If it takes 5 or 7, keep going. Strict counts are wrong; until-found is right.
- **First-principles thinking.** Challenge the requirement before optimizing the answer. Most "we have to do X" assumptions are habit, not necessity. Reduce to irreducible truths and rebuild from there.
- **Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away.** — Saint-Exupéry. The operating definition of "done." A change is finished when no further line, branch, flag, or doc paragraph can be removed without breaking a learned failure mode.

## Quick Start

```text
ideate (optional)  ->  resolve  ->  ship
```

- `/devlyn:ideate` (optional) — unstructured idea → `docs/specs/<id>/spec.md` + `spec.expected.json`. Modes: default Q&A, `--quick` (autonomous-pipeline-safe), `--from-spec <path>`, `--project` (multi-feature).
- `/devlyn:resolve` — hands-free pipeline for any coding task. Free-form goal, `--spec <path>`, or `--verify-only <ref> --spec <path>`. Phases run inline: PLAN → IMPLEMENT → BUILD_GATE → CLEANUP → VERIFY (fresh-subagent, findings-only).
- `/devlyn:design-ui` — required creative UI exploration surface. Spawns a 5-specialist design team (Creative Director, Product Designer, Visual Designer, Interaction Designer, Accessibility Designer) to generate N (default 5) portfolio-worthy HTML/CSS samples. Optional companion skills (`/devlyn:reap`, `/devlyn:design-system`) live in `optional-skills/` and install only when the user opts in.

Each skill's `SKILL.md` is the source of truth for flags and workflow. Do not duplicate.

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

- Unrequested work ("while here, also fix...").
- Tangential cleanup in files the task does not require.
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
- No engine-availability fallback is permitted for pair/risk-probe routes: if required Codex or Claude is unavailable, emit `BLOCKED:codex-unavailable` or `BLOCKED:claude-unavailable` with setup guidance. `--no-pair` and `--no-risk-probes` are explicit user opt-outs, not fallbacks.

## Evidence Over Claim

Every finding cites concrete evidence:

- Code: `file:line` you opened.
- Missing implementation: state exactly what you searched and found absent.
- Doc: cite the stale text + section/line.
- Browser: route/URL + screenshot or observed evidence.
- Benchmark: run id, fixture id, metric, raw result path.

Exclude vague claims. They produce vague fixes.

## Working In a devlyn-cli Project

- Check `git status --short` before editing.
- Never revert user changes unless explicitly asked.
- Use `rg` / `rg --files` for search.
- Keep changes scoped to the task; stop when the core request is answered or the change is verified.
- For installer or skill edits inside the devlyn-cli source repo, run `bash scripts/lint-skills.sh`.
- Treat the project's own `docs/VISION.md`, `docs/ROADMAP.md`, `docs/roadmap/**`, and any local `AGENTS.md` / `CLAUDE.md` overrides as authoritative when present.

## Communication

- Lead with objective evidence before opinion.
- Be concise and specific.
- State blockers plainly.
- Separate completed work, verification, and remaining risks.
