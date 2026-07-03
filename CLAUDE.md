# Project Instructions

devlyn-cli installs `/devlyn:ideate` (optional) and `/devlyn:resolve` (required) into Claude Code, plus the contract below. These principles are non-negotiable on every change — yours and any sub-agent's.

## Core principles

Seven rules govern every change. Cite them by name when a decision touches one.

1. **No workaround** — fix the root cause, never the symptom. Blocked patterns: `any`, `@ts-ignore`, silent `catch`, hardcoded fallback hiding a broken contract, config-level skip bypassing the real issue, helper script that routes around it. **Permitted exceptions** (widely-accepted defaults only): CSS fallback fonts, CDN failover, image placeholders. **No engine-availability fallback** for EXPLICITLY-requested `/devlyn:resolve` routes (`--engine`, `--risk-probes`, `--pair-verify`) — if the required engine is unavailable, stop with `BLOCKED:codex-unavailable` or `BLOCKED:claude-unavailable` and setup guidance; never downgrade an explicit route to solo. AUTOMATIC high-risk escalations (auto risk-probes / auto VERIFY pair) are capability-gated: they activate only when the OTHER engine is available; otherwise the run proceeds solo and reports the skip — route selection, not a fallback, and the reason single-LLM users stay first-class. `--no-pair` / `--no-risk-probes` remain explicit opt-outs.
2. **No overengineering** — smallest change that closes the goal. New abstractions require an observed failure mode they prevent. Subtractive-first: ask "what can I delete instead?" before writing anything new.
3. **No guesswork** — verify with the actual files, logs, diffs, and run output before forming conclusions. State the falsifiable prediction BEFORE the experiment; record raw results AFTER. Retroactive prediction edits are dishonest.
4. **Worldclass** — code that survives review at a non-trivial codebase. Zero CRITICAL, zero HIGH security/design findings on the shippable path.
5. **Best practice** — idiomatic for the language and framework. Use standard primitives; do not hand-roll what the library already provides.
6. **Optimized** — efficient on the resource that matters (wall-time, tokens, attention, cognitive load on the next reader). "Slower but more thoughtful" is not free. Each layer of composition or process must beat the simpler baseline.
7. **Production ready** — error states are explicit and visible; behavior under failure is what the user expects, not silent corruption.

Three discipline rules govern HOW the principles are applied:

- **Root cause via flexible why-chain.** Keep asking "why?" until you find the violated invariant. **If the answer surfaces in 2 questions, stop.** If it takes 5 or 7, keep going. Strict counts are wrong; until-found is right.
- **First-principles thinking.** Challenge the requirement before optimizing the answer. Surface unstated assumptions, ambiguities, tradeoffs, and simpler alternatives BEFORE implementing — do not silently pick one interpretation when multiple exist, do not hide confusion, push back when a simpler path is genuinely better. Most "we have to do X" assumptions are habit, not necessity. Reduce the problem to its irreducible truths and rebuild from there.
- **Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away.** — Saint-Exupéry. This is the operating definition of "done." A change is finished when no further line, branch, flag, or doc paragraph can be removed without breaking a learned failure mode. Not before.

The runtime sub-agent contract below (Subtractive-first / Goal-locked / No-workaround discipline / Evidence over claim) expands these principles into concrete operational tests. Sub-agents in `/devlyn:resolve` and `/devlyn:ideate` enforce them at every phase.

## Quick Start

Two skills cover the full cycle. `/devlyn:ideate` is OPTIONAL; `/devlyn:resolve` is REQUIRED; `/devlyn:design-ui` is also REQUIRED as the creative UI exploration surface. Engine selection follows the role map below.

1. `/devlyn:ideate` (optional) — unstructured idea → `docs/specs/<id>/spec.md` + `spec.expected.json`. Modes: default Q&A, `--quick` (autonomous-pipeline-safe), `--from-spec <path>`, `--project`.
2. `/devlyn:resolve` — hands-free pipeline for any coding task. Free-form goal, `--spec <path>`, or `--verify-only <diff> --spec <path>`. Phases: PLAN → IMPLEMENT → BUILD_GATE → CLEANUP → VERIFY (fresh subagent, findings-only).

Each skill's `SKILL.md` is the source of truth for its flags and workflow — don't duplicate them here.

### Engine roles — auto-detected, manually pinnable

| Role | Default | Manual override |
|---|---|---|
| Orchestrator — conversation, handoff, loop driving | whichever CLI you open (contract is symmetric: CLAUDE.md ↔ AGENTS.md) | switch CLIs; the file artifacts (spec/queue/state) carry over |
| Executor — PLAN/IMPLEMENT/CLEANUP + primary VERIFY judge | `claude` | `--engine <name>` per run, or `/devlyn:engines executor <name>` (durable pin) |
| Pair judge — VERIFY pair-JUDGE, risk probes | first available OTHER engine (claude↔codex) | `/devlyn:engines pair <name>,...`; `--no-pair` opts out |

`/devlyn:engines` with no args shows the current role table, detected engines, and how to pin or clear — the pins live in `.devlyn/engines.json`.

`.devlyn/engines.json` is machine-local — not committed, not archived. Pins are promises: a pinned unavailable engine stops with `BLOCKED:<engine>-unavailable`; a name without a `_shared/adapters/<name>.md` adapter stops with `BLOCKED:invalid-engine-config`. New engines (GLM, pi-agent backends) plug in by shipping an adapter file — no skill changes. Codex BUILD/IMPLEMENT and PLAN-pair remain research-only paths behind explicit `--engine codex`.

### Conversational handoff + loop engineering — the default entry for all work

The user does not invoke skills manually; the orchestrating model does. Small tasks: invoke `/devlyn:resolve "<goal>"` directly. Large tasks agreed in conversation:

1. Write the agreed contract to `docs/specs/<id>/spec.md` (+ `spec.expected.json` when mechanical verifications exist). Always a spec file for large work — never `--goal-file`, which routes into `BLOCKED:large-needs-ideation`.
2. Present a one-screen plan-contract summary — the user's single review checkpoint, BEFORE the pipeline starts.
3. On go-ahead, invoke `/devlyn:resolve --spec <path>` hands-free to completion.
4. **Per-task outer loop**: read the terminal verdict. PASS → done. Verdicts backed by spec/verification findings (NEEDS_WORK, verify/build-gate exhaustion) → adjudicate the findings, amend the spec (recorded in the spec file; spec stays read-only inside a run), re-invoke — at most 3 outer iterations, then surface with the findings trail. Infrastructure, invalid-input, engine-availability, and implement-empty BLOCKED verdicts are not spec-amendable: surface immediately. Every iteration re-enters through durable artifacts (spec, findings, run archive), never conversation memory.

**Intent queue (unattended drain)**: the user stacks intents in `docs/specs/queue.md` (ordered checklist; `/devlyn:queue` is the front-end — no args shows status, `add <intent>` appends, `drain` starts the serial drain). Drain strictly serially — per item: spec it, run the outer loop, mark `[x]` done or `[F]` blocked with reason, continue; a blocked item never halts the queue. The queue entry is the user's go-ahead, so assume-and-log replaces the interactive checkpoint — but unattended assumptions may only take scope-narrowing, reversible, non-user-visible defaults. Material ambiguity (user-visible behavior, data/state semantics, new files/scripts/flags, implementation surface) → mark `[F] needs-review` and move on. End the drain with a per-item verdict + assumptions report.

### Subtractive-first editing — perfection = nothing left to remove
<!-- runtime-principles:section=subtractive-first:begin -->

> **Operating definition of "done" in this repo** (Saint-Exupéry discipline rule above): a change is finished when no further line, branch, flag, or doc paragraph can be removed without breaking a learned failure mode. Not before.

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

1. **Unrequested work.** "While I'm here, I noticed X is broken/ugly/inefficient" → **stop**. The user did not ask for X. If X is a real defect, surface it as a finding, a follow-up suggestion, or an entry in a TODO list — do NOT fix it inside the current change. Mixing unrequested work with requested work is what makes diffs unreviewable and PRs eternal. **Pre-existing dead code → mention only, do NOT delete; orphans YOUR change created (now-unused imports, variables, functions) → clean them up.**
2. **Tangential cleanup.** "This file looks messy, let me also tidy..." → **stop**. The current task is the only task. Unrelated cleanup is a separate change requiring its own justification, scope, and pre-flight 0 check. **Match existing style even if you'd write it differently; do NOT touch comments, formatting, or code orthogonal to your real change** — silent side-effects on neighboring lines are the most common Karpathy-observed regression class.
3. **Speculative robustness.** "Just adding a check / fallback / handler for the case where..." → **stop**. If the case has not been observed (in production, in tests, in a finding), it does not belong in this change. Defensive code added for unobserved cases is the most common form of accretion debt — it never gets removed because nobody can prove the case never happens.
4. **Re-scoping mid-flight.** "Actually, the better way to do this is to also restructure / rename / migrate..." → **stop**. If you discover the requested approach is wrong, surface that to the user with evidence and let them adjudicate. Do NOT silently expand scope. The user's explicit redirect is the only authorization to enlarge a task.
5. **Curiosity detours.** "Let me also explore how Y works to understand this better..." → **stop**, unless Y is provably on the goal's critical path. Curiosity-driven exploration is creative-mode; default is execution-mode.

**The single drift test before any deviation from the stated goal:** *"Did the user ask for this, OR does the user's stated goal strictly require it?"* If the answer to both is no, do not do it. Surface it as a note (commit message, end-of-turn summary, finding) and continue on the original path.

**Creative-mode is the narrow exception, not the default.** Creative-mode applies only when (a) the user explicitly invoked an ideation/exploration surface (`/devlyn:ideate`, `/devlyn:design-ui`, "let's brainstorm", "explore options for"), OR (b) the goal is genuinely under-specified and a clarifying question is impossible (extremely rare — usually you should ask). For everything else — bug fixes, feature work, refactors, doc updates, pipeline runs, code review, debugging — execution-mode is the default and drift is a defect, not a feature.

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

### Evidence over claim
<!-- runtime-principles:section=evidence:begin -->

Every finding cites concrete evidence. Vague claims are speculation; exclude them.

- **Code findings**: `file:line` you have opened.
- **Missing findings**: explicit "searched X and found no implementation" statement.
- **Doc findings**: quote of the stale text + section/line reference.
- **Browser findings**: screenshot reference + URL/route.

**Negative existence claims** ("X lacks Y", "X cannot Z", "X is Y-specific") are the highest-risk shape — they feel like recall but fail to any single counter-example. They require active search at write time, not absence-of-memory. This rule applies to conversational answers and comparison-table cells, not only `/devlyn:resolve` findings — every cell of a trade-off table is a falsifiable claim.

**A position reversal is itself a claim.** In an oracle-less debate — design, strategy, trade-off, any decision with no spec or verifier to check against — changing your mind after a critique requires a NAMED DELTA: cite the specific prior claim, evidence, or criterion that changed, not a post-hoc rationale invented to justify a flip you were already going to make. Before reversing or choosing between contested positions, state each side's strongest form and the decisive criterion; the chosen outcome may adopt one side wholesale — synthesis means the best decision, not a forced blend. Flipping to whoever spoke last without a cited delta is capitulation, not reasoning; genuinely unresolved disagreement is escalated to the user, never closed by deferring to the last speaker. When you commission an adversarial review, require the critic to return the strongest counter, the strongest form of your own position, AND a synthesis — a refute-only mandate produces debate, not better decisions.

A finding without one of these forms is excluded. Vague findings produce vague fixes.
<!-- runtime-principles:section=evidence:end -->

## Codex invocation

When `/devlyn:resolve` or `/devlyn:ideate` route a phase to Codex (`--engine codex` or conditional VERIFY pair/risk-probe routing), the wrapper-form contract lives in `config/skills/_shared/codex-config.md` (or `.claude/skills/_shared/codex-config.md` once installed). Omit `-m <model>` — the CLI's current flagship is used automatically. MCP is not in the loop. If Codex is required and unavailable, stop with `BLOCKED:codex-unavailable` and setup guidance.

## Working Mode

- **Checkpoint with TaskCreate / TaskUpdate.** Long investigations or multi-phase work: create tasks at start, mark completed as each one closes — don't batch.
- **Don't stop early on token-budget concerns.** Context auto-compacts; the model resumes after compaction. Run the work to a real stopping point.
- **Persist across context windows via disk.** `/devlyn:resolve` writes `.devlyn/pipeline.state.json` plus per-phase log/findings under `.devlyn/runs/<run_id>/`; for ad-hoc long work use `HANDOFF.md` and resume with `@HANDOFF.md continue`.
- **Parallelize independent tool calls; reserve `Agent` subagents for independent fan-out or isolated-context verification** — a single perspective is the default on the resolve hot path.

## Skill Boundary Policy

The runtime pipeline surface is two skills — `/devlyn:resolve` and `/devlyn:ideate` — plus `/devlyn:design-ui` for creative UI exploration and two utilities added on explicit user direction: `/devlyn:engines` (engine-role config, iter-0038) and `/devlyn:queue` (intent-queue status/add/drain, iter-0039). `/devlyn:resolve` runs PLAN → IMPLEMENT → BUILD_GATE → CLEANUP → VERIFY inline; verification, cleanup, and security review (delegated to the native `security-review` Claude Code skill from BUILD_GATE) all live inside the pipeline. There are no standalone `/devlyn:review`, `/devlyn:evaluate`, or `/devlyn:team-resolve` surfaces. `/devlyn:design-ui` spawns a 5-specialist design team (Creative Director, Product Designer, Visual Designer, Interaction Designer, Accessibility Designer). `/devlyn:reap` is an optional user-invoked skill in `optional-skills/`; resolve never delegates to it.

Browser validation runs directly from BUILD_GATE using whichever toolchain is available (Chrome MCP, Playwright, or curl-tier fallback) — there is no separate `/devlyn:browser-validate` skill.

## Communication Style

Lead with **objective data** (popularity, benchmarks, community adoption) before opinions — especially when the user asks "what's popular" or "what do others use."

## Commit Conventions

Follow `.claude/commit-conventions.md`.

## Design System

When doing UI/UX work, follow `docs/design-system.md` if it exists.
