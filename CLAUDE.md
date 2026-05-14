# Project Instructions

devlyn-cli installs `/devlyn:ideate` (optional) and `/devlyn:resolve` (required) into Claude Code, plus the contract below. These principles are non-negotiable on every change — yours and any sub-agent's.

## Core principles

Seven rules govern every change. Cite them by name when a decision touches one.

1. **No workaround** — fix the root cause, never the symptom. No `any`, no `@ts-ignore`, no silent `catch`, no hardcoded fallback that hides a broken contract. Configuration-level skips that bypass the real issue are also rejects.
2. **No overengineering** — smallest change that closes the goal. New abstractions require an observed failure mode they prevent. Subtractive-first: ask "what can I delete instead?" before writing anything new.
3. **No guesswork** — verify with the actual files, logs, diffs, and run output before forming conclusions. State the falsifiable prediction BEFORE the experiment; record raw results AFTER. Retroactive prediction edits are dishonest.
4. **Worldclass** — code that survives review at a non-trivial codebase. Zero CRITICAL, zero HIGH security/design findings on the shippable path.
5. **Best practice** — idiomatic for the language and framework. Use standard primitives; do not hand-roll what the library already provides.
6. **Optimized** — efficient on the resource that matters (wall-time, tokens, attention, cognitive load on the next reader). "Slower but more thoughtful" is not free. Each layer of composition or process must beat the simpler baseline.
7. **Production ready** — error states are explicit and visible; behavior under failure is what the user expects, not silent corruption.

Three discipline rules govern HOW the principles are applied:

- **Root cause via flexible why-chain.** Keep asking "why?" until you find the violated invariant. **If the answer surfaces in 2 questions, stop.** If it takes 5 or 7, keep going. Strict counts are wrong; until-found is right.
- **First-principles thinking.** Challenge the requirement before optimizing the answer. Most "we have to do X" assumptions are habit, not necessity. Reduce the problem to its irreducible truths and rebuild from there.
- **Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away.** — Saint-Exupéry. This is the operating definition of "done." A change is finished when no further line, branch, flag, or doc paragraph can be removed without breaking a learned failure mode. Not before.

The runtime sub-agent contract below (Subtractive-first / Goal-locked / No-workaround discipline / Evidence over claim) expands these principles into concrete operational tests. Sub-agents in `/devlyn:resolve` and `/devlyn:ideate` enforce them at every phase.

## Quick Start

Two skills cover the full cycle post iter-0034 Phase 4 cutover (2026-05-04). `/devlyn:ideate` is OPTIONAL; `/devlyn:resolve` is REQUIRED; `/devlyn:design-ui` is also REQUIRED as the creative UI exploration surface. **Both pipeline skills default to `--engine claude`** for PLAN/IMPLEMENT. Codex BUILD/IMPLEMENT and PLAN-pair remain research-only, but `/devlyn:resolve` VERIFY has conditional-default pair-JUDGE when its `SKILL.md` trigger policy fires. Pass `--engine auto` or `--engine codex` explicitly to opt into the broader research path. If a selected or conditionally required engine is unavailable, the run stops with `BLOCKED:<engine>-unavailable` and setup guidance.

1. `/devlyn:ideate` (optional) — unstructured idea → `docs/specs/<id>/spec.md` + `spec.expected.json`. Modes: default Q&A, `--quick` (autonomous-pipeline-safe), `--from-spec <path>`, `--project`.
2. `/devlyn:resolve` — hands-free pipeline for any coding task. Free-form goal, `--spec <path>`, or `--verify-only <diff> --spec <path>`. Phases: PLAN → IMPLEMENT → BUILD_GATE → CLEANUP → VERIFY (fresh subagent, findings-only).

Each skill's `SKILL.md` is the source of truth for its flags and workflow — don't duplicate them here.

### When to use which

| Situation | Command |
|-----------|---------|
| New project / multi-feature plan / external spec to normalize | `/devlyn:ideate` (`--project`, default, or `--from-spec`) |
| One-line goal you want turned into a spec autonomously | `/devlyn:ideate --quick` |
| Spec already in hand | `/devlyn:resolve --spec <path>` |
| Free-form fix / feature / refactor / debug / PR review | `/devlyn:resolve "<describe the work>"` |
| Verify a diff or PR against a spec | `/devlyn:resolve --verify-only <ref> --spec <path>` |

### Subtractive-first editing — perfection = nothing left to remove
<!-- runtime-principles:section=subtractive-first:begin -->

> "Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away." — Saint-Exupéry. **This is the operating definition of "done" in this repo.** A change is finished when no further line, branch, flag, or doc paragraph can be removed without breaking a learned failure mode. Not before.

This rule overrides instinct. LLMs (including you) are trained on corpora that reward elaborate, defensive, "thorough" code — so the default impulse is to add. That impulse is wrong here. Read the rules below as hard tests, not aesthetic preferences. They are not optional, not negotiable, and not satisfiable by writing more careful additions.

**Mandatory pre-edit question.** Before writing any change, you must answer in this order:

1. **What can I delete that makes the addition unnecessary?** If the addition becomes redundant after the deletion, ship the deletion alone.
2. **What can I delete that makes the addition smaller?** Trim the surrounding accretion before adding.
3. **Only then**, what is the minimum addition required?

If you skip question 1 or 2, you are violating this rule even if the resulting code looks clean.

**Hard tests every edit must pass:**

- **Net-negative is the default; pure-addition needs a citation.** A diff that adds N lines and removes 0 must point to a specific cause: a previously-observed failure mode (commit hash, fixture ID, finding ID, user-reported incident), OR an explicit user request / spec requirement that demands new user-visible behavior. The latter is a sufficient citation — do not block legitimate requested additions on the absence of a past failure. What is rejected: vague justifications like "it seems clearer," "for future flexibility," "just in case," "to be safe," "for completeness," "to handle edge cases" — these are the exact phrases that produce accretion.
- **Delete the line that makes the bug impossible, not the line that catches it.** Defensive wrappers, validation layers, error normalizers, and `try/catch` shells are usually evidence that an upstream contract is unclear. Fix the contract upstream and remove the defenses downstream. The trap: adding the wrapper feels like progress because it makes a test pass. The wrapper is debt; the contract fix is the work. **Scope guard**: if the upstream contract fix is outside the user's stated scope, stop and surface the scope expansion to the user before editing — Goal-locked execution overrides this. The right scope-expansion outcome is "user authorizes the upstream fix" or "user accepts a scoped local fix and a follow-up for upstream"; never silently restructure something the user didn't ask you to.
- **A new flag, branch, or option is admitting two failures**: (a) the default was wrong, (b) every reader pays attention cost forever. Default-fix-and-delete-flag beats add-flag-with-better-default. The bar for adding a configuration knob is "I have observed two real users with genuinely conflicting needs," not "this might be useful someday."
- **Doc additions are subject to the same rule.** Before adding a section to any `.md` file (CLAUDE.md, SKILL.md, README, references/), find the now-stale sentence or section the new one supersedes — delete that first. A growing instructions file dilutes the instructions that actually need to be followed; readers (human and LLM) skim long files and miss load-bearing rules.
- **A "cleaner" refactor that grows line count is not cleaner.** It is a sideways move that increases context, parsing, and review cost. **For refactor-only changes**, line count must drop unless a cited observed failure requires the new shape. **Never delete tests, contracts, public API, comments documenting non-obvious WHY, or user-facing behavior just to win the count** — that is gaming the metric, not honoring the principle. The metric serves complexity reduction; if a deletion would lose information not recoverable from code + commit history, it is the wrong deletion.
- **Stop adding when no further deletion is possible.** This is the Saint-Exupéry test inverted into a stopping rule: if you have made an addition and you cannot identify anything else that can be removed, examine the addition itself — is part of it still removable? Iterate until the diff is irreducible.

**Anti-rationalization clause** — explicitly guarding against LLM-style hedging:

- "More explicit is safer" is **not** a justification. Explicitness has a cost in attention and rot. Required-explicit goes in; nice-to-explicit gets cut.
- "Adding context for future readers" is **not** a justification. Future readers benefit more from shorter files than from explanatory prose. The code and the commit message together carry the why.
- "Defense-in-depth" is **not** a justification at the harness layer. Two layers that catch the same bug are evidence one of them should be the only layer.
- If you find yourself writing the phrase "in case" in a comment, code reviewer note, or doc, **stop and re-evaluate** — that phrase predicts an unjustified addition.

**Stopping rule.** A change is done when (a) all hypotheses it was meant to close are closed, AND (b) you have attempted at least one further deletion and confirmed it would break something. If you have not tried to delete more, you are not done. If nothing can be deleted to justify the current addition, the addition itself is too large — re-scope or surface the conflict to the user before proceeding.

**Never grow surface area silently.** Every accretion-shaped change must be visible: in the commit message, in the iteration file, or in a flagged review. Silent growth is the failure mode this rule exists to prevent.
<!-- runtime-principles:section=subtractive-first:end -->

### Goal-locked execution — stay on the North Star, do not wander
<!-- runtime-principles:section=goal-locked:begin -->

Even with a North Star defined, work drifts off-course ("산으로 간다" / "삼천포로 빠진다" — going up the wrong mountain instead of forward). The harness must **actively block** this drift at run time, not merely discourage it. The default is ruler-straight execution toward the user's stated goal; any deviation requires explicit justification, not the inverse.

This rule exists because LLMs (including you) are trained to be helpful, comprehensive, and thorough — and "helpful" easily becomes "did more than asked." Doing more than asked is not helpfulness; it is scope creep. Read the rules below as hard blocks, not soft preferences.

**The five drift patterns you must refuse to execute on:**

1. **Unrequested work.** "While I'm here, I noticed X is broken/ugly/inefficient" → **stop**. The user did not ask for X. If X is a real defect, surface it as a finding, a follow-up suggestion, or an entry in a TODO list — do NOT fix it inside the current change. Mixing unrequested work with requested work is what makes diffs unreviewable and PRs eternal.
2. **Tangential cleanup.** "This file looks messy, let me also tidy..." → **stop**. The current task is the only task. Unrelated cleanup is a separate change requiring its own justification, scope, and pre-flight 0 check.
3. **Speculative robustness.** "Just adding a check / fallback / handler for the case where..." → **stop**. If the case has not been observed (in production, in tests, in a finding), it does not belong in this change. Defensive code added for unobserved cases is the most common form of accretion debt — it never gets removed because nobody can prove the case never happens.
4. **Re-scoping mid-flight.** "Actually, the better way to do this is to also restructure / rename / migrate..." → **stop**. If you discover the requested approach is wrong, surface that to the user with evidence and let them adjudicate. Do NOT silently expand scope. The user's explicit redirect is the only authorization to enlarge a task.
5. **Curiosity detours.** "Let me also explore how Y works to understand this better..." → **stop**, unless Y is provably on the goal's critical path. Curiosity-driven exploration is creative-mode; default is execution-mode.

**The single drift test before any deviation from the stated goal:** *"Did the user ask for this, OR does the user's stated goal strictly require it?"* If the answer to both is no, do not do it. Surface it as a note (commit message, end-of-turn summary, finding) and continue on the original path.

**Creative-mode is the narrow exception, not the default.** Creative-mode applies only when (a) the user explicitly invoked an ideation/exploration surface (`/devlyn:ideate`, optional `/devlyn:design-system`, "let's brainstorm", "explore options for"), OR (b) the goal is genuinely under-specified and a clarifying question is impossible (extremely rare — usually you should ask). For everything else — bug fixes, feature work, refactors, doc updates, pipeline runs, code review, debugging — execution-mode is the default and drift is a defect, not a feature.

**Anti-rationalization clause** — explicitly guarding against LLM hedging:

- "It's a small extra change" is **not** a justification. Small accretions compound; one of them is always small.
- "It's related to what they asked for" is **not** a justification. Related ≠ requested. Requested is the only standard.
- "It would be incomplete without this" is **not** a justification. The user defines completeness, not your sense of it.
- "I'm being thorough" is **not** a justification. Thoroughness on the requested goal is required; thoroughness extending past the goal is drift.

**When in doubt, ask — outside hands-free pipelines.** In interactive sessions a short clarification ("the requested fix touches the X code path; I notice Y also looks broken — should I fix it in this change or surface it as a follow-up?") is always cheaper than a wrong-scope diff. Asking is not a weakness; silently expanding scope is. **Inside hands-free pipelines** (`/devlyn:resolve`, scheduled remote agents, autonomous skill runs) the contract forbids mid-pipeline prompts — there asking is unsafe because there is no user to answer. The substitute is: stay strictly on the requested goal, do not expand scope, and log the question/assumption explicitly in the final report (or `.devlyn/runs/<run_id>/` artifacts) so the user can adjudicate after the run completes. Choosing scope creep over logging-and-staying-on-path is always wrong.

**Stopping rule.** A task is done when the user's stated goal is closed AND no off-path work was added. If you find yourself hesitating because "I should also do Z" — Z is drift. Note it for follow-up, do not execute.
<!-- runtime-principles:section=goal-locked:end -->

## Error Handling Philosophy

**No silent fallbacks.** Handle errors explicitly and show the user what happened.

- **Default**: when something fails, display a clear error state — message, retry option, or actionable guidance. Do NOT silently fall back to default/placeholder data.
- **Fallbacks are the exception.** Only use them when it's a widely accepted best practice (CSS fallback fonts, CDN failover, image placeholders). Otherwise handle the error explicitly.
- **Pattern**: `try { doThing() } catch (error) { showErrorUI(error) }` — NOT `try { doThing() } catch { return fallbackValue }`.

### No-workaround discipline (runtime salience)
<!-- runtime-principles:section=no-workaround:begin -->

No `any`, no `@ts-ignore`, no silent `catch`, no hardcoded values, no helper scripts that bypass the root cause. Fix root causes; handle errors with user-visible state per the rule above.

**Permitted exceptions** (explicitly carved out):
- CSS fallback fonts, CDN failover, image placeholders — widely-accepted best practices.
- No engine-availability fallback is permitted for `/devlyn:resolve` pair/risk-probe routes. If Codex or Claude is required and unavailable, the run stops with `BLOCKED:codex-unavailable` or `BLOCKED:claude-unavailable` plus setup guidance. `--no-pair` / `--no-risk-probes` are explicit user opt-outs, not fallbacks.
<!-- runtime-principles:section=no-workaround:end -->

### Evidence over claim
<!-- runtime-principles:section=evidence:begin -->

Every finding cites concrete evidence. Vague claims are speculation; exclude them.

- **Code findings**: `file:line` you have opened.
- **Missing findings**: explicit "searched X and found no implementation" statement.
- **Doc findings**: quote of the stale text + section/line reference.
- **Browser findings**: screenshot reference + URL/route.

A finding without one of these forms is excluded. Vague findings produce vague fixes.
<!-- runtime-principles:section=evidence:end -->

## Codex invocation

When `/devlyn:resolve` or `/devlyn:ideate` route a phase to Codex (`--engine codex`, `--engine auto`, or conditional VERIFY pair/risk-probe routing), the wrapper-form contract lives in `config/skills/_shared/codex-config.md` (or `.claude/skills/_shared/codex-config.md` once installed). Omit `-m <model>` — the CLI's current flagship is used automatically. MCP is not in the loop. If Codex is required and unavailable, stop with `BLOCKED:codex-unavailable` and setup guidance.

## Working Mode

- **Checkpoint with TaskCreate / TaskUpdate.** Long investigations or multi-phase work: create tasks at start, mark completed as each one closes — don't batch.
- **Don't stop early on token-budget concerns.** Context auto-compacts; the model resumes after compaction. Run the work to a real stopping point.
- **Persist across context windows via disk.** `/devlyn:resolve` writes `.devlyn/pipeline.state.json` plus per-phase log/findings under `.devlyn/runs/<run_id>/`; for ad-hoc long work use `HANDOFF.md` and resume with `@HANDOFF.md continue`.
- **Parallelize independent tool calls; reserve `Agent` subagents for independent fan-out or isolated-context verification** — a single perspective is the default on the resolve hot path.

## Skill Boundary Policy

Post iter-0034 Phase 4 cutover (2026-05-04) the runtime pipeline surface is two skills — `/devlyn:resolve` and `/devlyn:ideate` — plus the required creative UI exploration surface `/devlyn:design-ui`. `/devlyn:resolve` runs PLAN → IMPLEMENT → BUILD_GATE → CLEANUP → VERIFY inline; verification, cleanup, and security review (delegated to the native `security-review` Claude Code skill from BUILD_GATE) all live inside the pipeline. There are no standalone `/devlyn:review`, `/devlyn:evaluate`, `/devlyn:team-resolve`, etc. surfaces to delegate to — those skills were folded into resolve's phases or removed in iter-0034. `/devlyn:design-ui` is the unified creative UI exploration surface — it spawns a 5-specialist design team (Creative Director, Product Designer, Visual Designer, Interaction Designer, Accessibility Designer) by default for any N. The legacy `/devlyn:team-design-ui` was merged into it on 2026-05-14 and the optional-skills directory deleted. Optional creative power-user skills (`/devlyn:reap`, `/devlyn:design-system`) live in `optional-skills/` and are user-invoked only; resolve never delegates to them.

Browser validation routes through `_shared/browser-runner.sh` (Chrome MCP → Playwright → curl tier) directly from BUILD_GATE — there is no separate `/devlyn:browser-validate` skill at HEAD.

## Communication Style

Lead with **objective data** (popularity, benchmarks, community adoption) before opinions — especially when the user asks "what's popular" or "what do others use."

## Commit Conventions

Follow `.claude/commit-conventions.md`.

## Design System

When doing UI/UX work, follow `docs/design-system.md` if it exists.
