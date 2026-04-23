# Project Instructions

## Quick Start

Three commands cover most work. All default to `--engine auto` — Codex GPT-5.4 builds, Claude Opus 4.7 critiques (cross-model GAN dynamic).

1. `/devlyn:ideate` — unstructured idea → VISION/ROADMAP/item specs
2. `/devlyn:auto-resolve "Implement per spec at docs/roadmap/phase-N/X-name.md"` — hands-free build → evaluate → ship
3. `/devlyn:preflight` — verify the implementation matches the roadmap

Each skill's `SKILL.md` is the source of truth for its flags and workflow — don't duplicate them here.

## Harness Principles (Karpathy 4)

Every skill in this repo is an instance of these four. Apply them to the edit in front of you before adding anything new.

1. **Think Before Coding** — surface hidden assumptions. If a step looks obvious, name the assumption it rests on; if the assumption is wrong, the step is wrong.
2. **Simplicity First** — delete before you add. A prompt line, a phase, a template — if removing it does not break a learned failure mode, it is cost without value.
3. **Surgical Changes** — touch only what the goal requires. No opportunistic refactors inside a fix, no "while I'm here" drift. The diff size is a feature, not an accident.
4. **Goal-Driven Execution** — hand the subagent a goal and an acceptance check, not a procedure. If you're writing step-by-step instructions, ask whether the verification loop can catch the failure instead.

The current harness is already the product of many surgical passes. The next change should be equally targeted.

## Error Handling Philosophy

**No silent fallbacks.** Handle errors explicitly and show the user what happened.

- **Default**: when something fails, display a clear error state — message, retry option, or actionable guidance. Do NOT silently fall back to default/placeholder data.
- **Fallbacks are the exception.** Only use them when it's a widely accepted best practice (CSS fallback fonts, CDN failover, image placeholders). Otherwise handle the error explicitly.
- **Pattern**: `try { doThing() } catch (error) { showErrorUI(error) }` — NOT `try { doThing() } catch { return fallbackValue }`.

### Documented exception — Codex CLI availability downgrade

The `--engine auto` availability-check-and-downgrade rule (auto-resolve / ideate / preflight) is the one permitted silent fallback in this repo. It exists because the hands-free contract would otherwise abort every run when the local `codex` CLI is unavailable — a worse failure than running on Claude alone. The downgrade is not invisible: the final report header always prints `engine downgraded: codex-unavailable`, and the surfaced verdict is identical to an explicit `--engine claude` invocation. Any other silent fallback in skills code is a bug — file it against the skill that introduced it.

## Codex invocation

Skills call Codex via the local `codex exec` CLI (shipped by the `openai-codex` Claude Code plugin). See `config/skills/_shared/codex-config.md` for the canonical flag set. Omit `-m <model>`; the CLI's current flagship (today `gpt-5.4`, automatically whatever ships next) is used — zero-touch on upgrades. MCP is not in the loop.

## Working Mode

- **Checkpoint with TaskCreate / TaskUpdate.** Long investigations or multi-phase work: create tasks at start, mark completed as each one closes — don't batch.
- **Don't stop early on token-budget concerns.** Context auto-compacts; the model resumes after compaction. Run the work to a real stopping point.
- **Persist across context windows via disk.** auto-resolve writes `.devlyn/runs/<run_id>/` (`pipeline.state.json`, `<phase>.findings.jsonl`, `<phase>.log.md`); preflight writes `.devlyn/PREFLIGHT-REPORT.md`; for ad-hoc long work use `HANDOFF.md` and resume with `@HANDOFF.md continue`.
- **Fan out with `/devlyn:team-resolve` or parallel `Agent` subagents** when a single perspective isn't enough.

## Communication Style

Lead with **objective data** (popularity, benchmarks, community adoption) before opinions — especially when the user asks "what's popular" or "what do others use."

## Commit Conventions

Follow `.claude/commit-conventions.md`.

## Design System

When doing UI/UX work, follow `docs/design-system.md` if it exists.
