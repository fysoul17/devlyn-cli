# Project Instructions

## Quick Start

Three commands cover most work. All default to `--engine auto` — Codex GPT-5.4 builds, Claude Opus 4.7 critiques (cross-model GAN dynamic).

1. `/devlyn:ideate` — unstructured idea → VISION/ROADMAP/item specs
2. `/devlyn:auto-resolve "Implement per spec at docs/roadmap/phase-N/X-name.md"` — hands-free build → evaluate → ship
3. `/devlyn:preflight` — verify the implementation matches the roadmap

Each skill's `SKILL.md` is the source of truth for its flags and workflow — don't duplicate them here.

## Error Handling Philosophy

**No silent fallbacks.** Handle errors explicitly and show the user what happened.

- **Default**: when something fails, display a clear error state — message, retry option, or actionable guidance. Do NOT silently fall back to default/placeholder data.
- **Fallbacks are the exception.** Only use them when it's a widely accepted best practice (CSS fallback fonts, CDN failover, image placeholders). Otherwise handle the error explicitly.
- **Pattern**: `try { doThing() } catch (error) { showErrorUI(error) }` — NOT `try { doThing() } catch { return fallbackValue }`.

## Investigation Workflow

When investigating bugs, analyzing features, or exploring code:

1. **Define exit criteria upfront** — ask "what does 'done' look like?" before starting.
2. **Checkpoint progress** — use `TaskCreate`/`TaskUpdate` every 5–10 minutes.
3. **Intermediate summaries** — output "current understanding" snapshots so work isn't lost if interrupted.
4. **Always deliver findings** — never end mid-analysis. Minimum output: files examined, key findings, remaining unknowns, recommended next steps.

For complex investigations, use `/devlyn:team-resolve` for a multi-perspective team, or spawn parallel `Agent` subagents.

## Context Window Management

Claude 4.5/4.6/4.7 auto-compact as context approaches the limit — you can work indefinitely without manual handoffs in most cases. Don't stop early due to token-budget concerns; the model resumes from where it left off after compaction.

For multi-context-window work (e.g., a large roadmap), persist state to disk:
- auto-resolve writes durable state to `.devlyn/runs/<run_id>/` (pipeline.state.json, `<phase>.findings.jsonl`, `<phase>.log.md`) plus git commits. Pick up by reading `state.json` first; drill into JSONL/log files as needed.
- preflight writes `.devlyn/PREFLIGHT-REPORT.md`.
- For long investigations, write progress to `HANDOFF.md`; resume with `@HANDOFF.md continue`.

Manually `/clear` only when context is genuinely irrelevant to the next task.

## Communication Style

- Lead with **objective data** (popularity, benchmarks, community adoption) before personal opinions.
- When the user asks "what's popular" or "what do others use", answer with data.
- Keep recommendations actionable and specific.

## Commit Conventions

Follow `.claude/commit-conventions.md`.

## Design System

When doing UI/UX work, follow `docs/design-system.md` if it exists.
