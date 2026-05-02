# Codex Project Instructions

This file is the Codex counterpart to `CLAUDE.md`. `devlyn-cli` installs agent-facing project instructions and Claude Code skills into user projects, so these instructions must work both for this harness repository and for downstream projects that receive the file through the installer.

## Product Purpose

`devlyn-cli` is a context-engineering and harness-engineering toolkit. It installs structured prompts, Claude Code skills, agent configuration, and optional add-ons that turn normal development work into repeatable pipelines:

```text
ideate -> auto-resolve -> preflight -> fix gaps -> ship
```

Primary commands:

- `/devlyn:ideate` turns an idea into `docs/VISION.md`, `docs/ROADMAP.md`, and implementation-ready item specs.
- `/devlyn:auto-resolve` runs the autonomous build/evaluate/fix/review/docs pipeline.
- `/devlyn:preflight` audits the codebase against the vision, roadmap, and specs.
- Manual tools include `/devlyn:resolve`, `/devlyn:review`, `/devlyn:team-review`, `/devlyn:clean`, `/devlyn:update-docs`, and UI design/implementation skills.

Each skill's `SKILL.md` is the source of truth for its flags and workflow. Do not duplicate detailed skill contracts here.

## Scope Split

There are two audiences. Keep them separate.

- **Runtime skills / downstream user projects**: follow the runtime contract in `config/skills/_shared/runtime-principles.md` when available. Skills should not cite this harness-development contract to users.
- **Harness development / autoresearch loop**: evolve `devlyn-cli` itself according to `autoresearch/NORTH-STAR.md`, `autoresearch/PRINCIPLES.md`, and `autoresearch/HANDOFF.md`.

When working inside this repository, read `autoresearch/HANDOFF.md` before non-trivial changes. It records branch state, in-flight work, current experimental evidence, and rejected paths.

## Non-Negotiable Principles

Every meaningful change is checked against these principles:

1. **No overengineering**: make the smallest change that closes the hypothesis. Prefer deletion before addition. New abstractions require an observed failure mode they prevent.
2. **No guesswork**: inspect the actual files, logs, diffs, and docs before forming conclusions. Make falsifiable predictions before experiments and record raw results after.
3. **No workaround**: fix root causes. No `any`, no `@ts-ignore`, no silent catches, no hardcoded fallbacks, and no helper scripts that bypass the real issue.
4. **Worldclass production-ready**: zero CRITICAL and zero HIGH design/security findings on the shippable path. Fixture-level blockers cannot be averaged away.
5. **Best practice**: use idiomatic language/framework primitives. Do not hand-roll helpers that replace standard library or framework behavior without evidence.
6. **Layer-cost-justified**: every extra model, agent, phase, or composition layer must beat the simpler baseline on both quality and wall-time efficiency.

## Subtractive-First Editing

Before writing any change, answer in this order:

1. What can I delete that makes the addition unnecessary?
2. What can I delete that makes the addition smaller?
3. What is the minimum addition still required?

Hard rules:

- A pure-addition diff needs a citation: an explicit user/spec requirement or an observed failure mode.
- Refactor-only changes should reduce line count unless a real failure requires the new shape.
- Do not add flags, branches, or options for hypothetical users.
- Do not add defensive wrappers when an upstream contract can be corrected instead.
- Doc growth has the same cost as code growth. Delete stale or superseded prose before adding new prose.
- A change is not done until you have attempted one more deletion and confirmed it would break something.

## Goal-Locked Execution

Default mode is execution toward the user's stated goal. Do not drift.

Refuse these patterns:

- Unrequested work: "while here, also fix..."
- Tangential cleanup in files the task does not require.
- Speculative robustness for cases not observed in production, tests, findings, or the spec.
- Mid-flight re-scoping without user approval.
- Curiosity exploration that is not on the critical path.

The drift test: **Did the user ask for this, or does the stated goal strictly require it?** If not, surface it as a follow-up note instead of editing it.

In interactive sessions, ask a concise clarification when scope expansion is real. In hands-free pipelines, do not pause for prompts; stay on scope and log the assumption/follow-up in the final artifact.

## Error Handling

No silent fallbacks.

- Show clear errors, retry paths, or actionable guidance.
- Fallbacks are allowed only when they are widely accepted and harmless, such as CSS fallback fonts, CDN failover, or image placeholders.
- Silent `catch` blocks are bugs.
- Logging is not user-visible error handling.
- The documented Codex CLI availability downgrade is the one known exception in this harness: it must emit the `engine downgraded: codex-unavailable` banner and behave exactly like explicit Claude routing.

## Evidence Over Claim

Every finding must cite concrete evidence.

- Code finding: `file:line` you opened.
- Missing implementation: state exactly what you searched and found absent.
- Doc finding: cite the stale text and section/line.
- Browser finding: include route/URL and screenshot or equivalent observed evidence.
- Benchmark or experiment claim: cite run id, fixture id, metric, and raw result path.

Exclude vague claims. Vague findings create vague fixes.

## Codex / Multi-Model Use

Do not delegate decisions to another model. Reason independently first, then use cross-model review as falsification.

When this repository asks for Codex companion review, use the monitored wrapper documented in `config/skills/_shared/codex-config.md` and `CLAUDE.md`. Send rich evidence and a draft conclusion; ask for disproof, not permission.

Keep runtime cost separate from harness-development cost:

- Harness development can use pair review more freely because improvements amortize across future runs.
- Runtime user-task pipelines must aggressively gate pair calls because every extra phase costs the user time and tokens.

## Working In This Repository

- Check `git status --short` before editing.
- Never revert user changes unless explicitly asked.
- Use `rg` / `rg --files` for search.
- Use `apply_patch` for manual edits.
- Keep changes scoped to the task.
- Run `bash scripts/lint-skills.sh` after changes to skills, runtime principles, installer logic, README/CLAUDE/AGENTS guidance, or critical harness docs.
- For CLI code changes, run the narrow Node/script validation that exercises the touched path.
- Follow `config/commit-conventions.md` for commits.

Important files:

- `bin/devlyn.js`: installer and CLI entrypoint.
- `config/skills/`: installed Claude Code skills.
- `config/skills/_shared/runtime-principles.md`: runtime sub-agent contract.
- `agents-config/`: instructions installed for other AI CLIs.
- `autoresearch/`: harness experiments, decisions, handoffs, and North Star.
- `benchmark/auto-resolve/`: benchmark fixtures and A/B evaluation harness.

## Installed Project Guidance

When this file is installed into another project:

- Treat that project's own `AGENTS.md`, `CLAUDE.md`, `docs/VISION.md`, `docs/ROADMAP.md`, and `docs/roadmap/**` as local source of truth when present.
- Prefer `/devlyn:ideate -> /devlyn:auto-resolve -> /devlyn:preflight` for substantial product work.
- For small direct fixes, inspect the code, make the minimal scoped change, and run relevant validation.
- Preserve the same principles: no workaround, no guesswork, no overengineering, worldclass production-ready, best practice, evidence over claim.

## Communication

- Lead with objective evidence before opinion.
- Be concise and specific.
- State blockers plainly.
- Separate completed work, verification, and remaining risks.

