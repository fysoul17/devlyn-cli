# Project Instructions

## Outer goal — read first if you do not already know it

The harness composes frontier LLMs into a hands-free pipeline that delivers engineer-quality software for users who do not know context engineering. Two first-class user groups: single-LLM (Opus alone, GPT-5.5 alone) and multi-LLM (Claude + Codex). Three composition layers: **L0** bare LLM, **L1** solo harness on a single LLM, **L2** pair harness with `solo` / `pair_critic` / `pair_consensus` modes per phase. Each layer must beat the previous on **both quality and wall-time efficiency** — concretely, each layer must beat `previous-layer-best-of-N` where N is the wall-time ratio.

Full contract: [`autoresearch/NORTH-STAR.md`](autoresearch/NORTH-STAR.md). Per-iteration doctrine: [`autoresearch/PRINCIPLES.md`](autoresearch/PRINCIPLES.md). Branch-state + in-flight work: [`autoresearch/HANDOFF.md`](autoresearch/HANDOFF.md).

## Quick Start

Three commands cover most work. All default to `--engine auto` — the Codex CLI's flagship model builds, Claude critiques (cross-model GAN dynamic). No model versions are hardcoded; the CLI's current flagship is inherited automatically.

1. `/devlyn:ideate` — unstructured idea → VISION/ROADMAP/item specs
2. `/devlyn:auto-resolve "Implement per spec at docs/roadmap/phase-N/X-name.md"` — hands-free build → evaluate → ship
3. `/devlyn:preflight` — verify the implementation matches the roadmap

Each skill's `SKILL.md` is the source of truth for its flags and workflow — don't duplicate them here.

### When to use which

| Situation | Command |
|-----------|---------|
| New project or shifting direction | `/devlyn:ideate` (greenfield) |
| Existing roadmap, new feature/bug idea | `/devlyn:ideate` (quick add) |
| One spec ready to implement | `/devlyn:auto-resolve "Implement per spec at …"` |
| Roadmap complete, need verification | `/devlyn:preflight` |
| Focused debugging (no pipeline) | `/devlyn:resolve` |
| Manual post-change review | `/devlyn:review` or `/devlyn:team-review` |

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

Skills call Codex via the local `codex exec` CLI (shipped by the `openai-codex` Claude Code plugin). See `config/skills/_shared/codex-config.md` for the canonical flag set. Omit `-m <model>`; the CLI's current flagship (today `gpt-5.5`, automatically whatever ships next) is used — zero-touch on upgrades. MCP is not in the loop.

## Working Mode

- **Checkpoint with TaskCreate / TaskUpdate.** Long investigations or multi-phase work: create tasks at start, mark completed as each one closes — don't batch.
- **Don't stop early on token-budget concerns.** Context auto-compacts; the model resumes after compaction. Run the work to a real stopping point.
- **Persist across context windows via disk.** auto-resolve writes `.devlyn/runs/<run_id>/` (`pipeline.state.json`, `<phase>.findings.jsonl`, `<phase>.log.md`); preflight writes `.devlyn/PREFLIGHT-REPORT.md`; for ad-hoc long work use `HANDOFF.md` and resume with `@HANDOFF.md continue`.
- **Fan out with `/devlyn:team-resolve` or parallel `Agent` subagents only for explicit complex scope** — a single perspective is the default on the auto-resolve hot path.

## Skill Boundary Policy

auto-resolve's phases are **inline by default**. The standalone skills `/devlyn:evaluate`, `/devlyn:review`, `/devlyn:team-review`, `/devlyn:team-resolve`, `/devlyn:clean`, `/devlyn:update-docs` are **manual tools** — auto-resolve does not invoke them. The four findings-producing standalones (`evaluate`, `review`, `clean`, `team-review`) emit a `.devlyn/<skill>.findings.jsonl` sidecar matching the shared schema at `config/skills/devlyn:auto-resolve/references/findings-schema.md`, so a manual run produces artifacts compatible with the pipeline view. The two action-producing standalones (`team-resolve`, `update-docs`) write code or docs directly and have no findings schema to share. The invocation boundary is clean in both cases.

auto-resolve delegates to another skill **only** when one of these is true:

1. The delegate has exclusive capability — native `security-review`, Chrome MCP via `/devlyn:browser-validate`, team assembly via `--team`.
2. The work is off the bare path **and** explicitly complex (`--team` flag or `state.route.selected == "strict"`).
3. The user invoked a standalone directly — `/devlyn:auto-resolve` does not call it for them.

This boundary is deliberate. The earlier attempt to absorb every standalone into the pipeline diverged contracts (interactive prompts, markdown vs JSONL output, code-mutating reviewers), and the token math on delegation inflated the bare-case run. Changing this rule requires an A/B proof that bare-case wall-time and tokens do not regress.

## Native Claude Code Skills

- Use **native `security-review`** for the CRITIC security sub-pass. Do not build a custom `/devlyn:security-audit`. Native is findings-only (compatible with the post-EVAL invariant) and covers the same OWASP surface without the Dual-model token cost.
- Do **not** use native `simplify` inside auto-resolve. Native simplify mutates code, which violates the post-EVAL findings-only invariant. EVAL already covers simplify's concerns (duplication, reuse, pattern violations) at full CRITICAL/HIGH/MEDIUM severity via `architecture.*` findings.

## Bare-Case Guardrail

The modal run — single spec, solo build, no browser, standard route, PASS on first EVAL, clean CRITIC, no fix loops — is the primary performance target. No new hot-path phase, no sub-skill delegation, and no instrumentation may land without an A/B proof that this case's wall-time and tokens do not regress. Complex cases may cost more; the bare case may not.

## No-Workaround Bar

No `any`, no `@ts-ignore`, no silent `catch`, no hardcoded values. Fix root causes. Handle errors explicitly with user-visible state (per `Error Handling Philosophy`). The one documented silent fallback — Codex CLI availability downgrade — has a banner in the final report and a verdict identical to `--engine claude`.

## Communication Style

Lead with **objective data** (popularity, benchmarks, community adoption) before opinions — especially when the user asks "what's popular" or "what do others use."

## Commit Conventions

Follow `.claude/commit-conventions.md`.

## Design System

When doing UI/UX work, follow `docs/design-system.md` if it exists.
