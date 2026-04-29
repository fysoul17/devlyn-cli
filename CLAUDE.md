# Project Instructions

## Outer goal — read first if you do not already know it

**This block is for the harness developer / autoresearch loop, not for run-time skills.** Skills (`/devlyn:auto-resolve`, `/devlyn:ideate`, `/devlyn:preflight`, etc.) are the *product* this contract is meant to evolve into world-class software — they should not themselves cite the contract.

**Goal**: the harness composes frontier LLMs into a hands-free pipeline that delivers engineer-quality software for users who do not know context engineering. Two first-class user groups: single-LLM (Opus alone, GPT-5.5 alone) and multi-LLM (Claude + Codex). Three composition layers: **L0** bare LLM, **L1** solo harness on a single LLM, **L2** pair harness with `solo` / `pair_critic` / `pair_consensus` modes per phase. Each layer must beat the previous on **both quality and wall-time efficiency** — concretely, each layer must beat `previous-layer-best-of-N` where N is the wall-time ratio.

**Five principles** every iteration is checked against (canonical in [`autoresearch/PRINCIPLES.md`](autoresearch/PRINCIPLES.md), summarized so a fresh session has them in working memory without opening another file):

1. **No overengineering** — smallest change that closes the hypothesis; new abstractions require an observed failure mode they prevent. **Subtractive-first**: before adding a line, file, abstraction, or flag, ask "what can I delete instead?" Net-deletions and net-additions are NOT equally good defaults — when both close the hypothesis, deletion wins. A change that only adds is suspect until justified.
2. **No guesswork** — falsifiable hypothesis BEFORE the experiment, predicted metric/direction filled in BEFORE the run, raw data filled in AFTER (no retroactive prediction edits).
3. **No workaround** — root-cause fixes via 3+ step why-chain. No `any`, no `@ts-ignore`, no silent catches, no hardcoded fallbacks. Configuration-level skips in skill iters are also rejects.
4. **Worldclass production-ready** — zero CRITICAL, zero HIGH `design.*` / `security.*` findings on the variant arm; aggregate margin can never excuse a fixture-level ship-blocker.
5. **Best practice** — idiomatic for the language/framework; zero MEDIUM `design.unidiomatic-pattern` findings (no hand-rolled helpers replacing standard primitives).
6. **Layer-cost-justified** — each composition layer beats `previous-layer-best-of-N` on both quality and wall-time efficiency; pair-mode phases must declare a deterministic short-circuit rule and a wall-time budget abort.

Full contract: [`autoresearch/NORTH-STAR.md`](autoresearch/NORTH-STAR.md). Per-iteration doctrine: [`autoresearch/PRINCIPLES.md`](autoresearch/PRINCIPLES.md). Branch-state + in-flight work: [`autoresearch/HANDOFF.md`](autoresearch/HANDOFF.md).

## Quick Start

Three commands cover most work. **`/devlyn:auto-resolve` defaults to `--engine claude`** post iter-0020 close-out — its experimental dual-engine `--engine auto` mode is currently disabled by default because it costs more and regresses quality on the 9-fixture benchmark suite (see [`autoresearch/iterations/0020-pair-policy-narrow.md`](autoresearch/iterations/0020-pair-policy-narrow.md)); pass `--engine auto` explicitly to opt into the research path. **`/devlyn:ideate` and `/devlyn:preflight` keep `--engine auto` as their default** — they have no measured pair-mode failure and use the cross-model GAN-critic dynamic deliberately.

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
2. **Simplicity First** — delete before you add (full operational rule below).
3. **Surgical Changes** — touch only what the goal requires (full operational rule below in "Goal-locked execution").
4. **Goal-Driven Execution** — hand the subagent a goal and an acceptance check, not a procedure. If you're writing step-by-step instructions, ask whether the verification loop can catch the failure instead.

The current harness is already the product of many surgical passes. The next change should be equally targeted.

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

**Creative-mode is the narrow exception, not the default.** Creative-mode applies only when (a) the user explicitly invoked an ideation/exploration surface (`/devlyn:ideate`, `/devlyn:design-ui`, "let's brainstorm", "explore options for"), OR (b) the goal is genuinely under-specified and a clarifying question is impossible (extremely rare — usually you should ask). For everything else — bug fixes, feature work, refactors, doc updates, pipeline runs, code review, debugging — execution-mode is the default and drift is a defect, not a feature.

**Anti-rationalization clause** — explicitly guarding against LLM hedging:

- "It's a small extra change" is **not** a justification. Small accretions compound; one of them is always small.
- "It's related to what they asked for" is **not** a justification. Related ≠ requested. Requested is the only standard.
- "It would be incomplete without this" is **not** a justification. The user defines completeness, not your sense of it.
- "I'm being thorough" is **not** a justification. Thoroughness on the requested goal is required; thoroughness extending past the goal is drift.

**When in doubt, ask — outside hands-free pipelines.** In interactive sessions a short clarification ("the requested fix touches the X code path; I notice Y also looks broken — should I fix it in this change or surface it as a follow-up?") is always cheaper than a wrong-scope diff. Asking is not a weakness; silently expanding scope is. **Inside hands-free pipelines** (`/devlyn:auto-resolve`, scheduled remote agents, autonomous skill runs) the contract forbids mid-pipeline prompts — there asking is unsafe because there is no user to answer. The substitute is: stay strictly on the requested goal, do not expand scope, and log the question/assumption explicitly in the final report (or `.devlyn/runs/<run_id>/` artifacts) so the user can adjudicate after the run completes. Choosing scope creep over logging-and-staying-on-path is always wrong.

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
- Codex CLI availability downgrade — the one documented silent fallback in this repo. Fires when the resolved engine is `auto` or `codex` (either via skill default or explicit `--engine` flag) and the Codex CLI is absent. Banner `engine downgraded: codex-unavailable` always prints; verdict identical to `--engine claude`. Any other silent fallback in skills code is a bug — file it against the skill that introduced it.
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

Skills call Codex via the local `codex exec` CLI (shipped by the `openai-codex` Claude Code plugin). See `config/skills/_shared/codex-config.md` for the canonical flag set. Omit `-m <model>`; the CLI's current flagship (today `gpt-5.5`, automatically whatever ships next) is used — zero-touch on upgrades. MCP is not in the loop.

### Codex companion pair-review (autoresearch loop, NOT runtime skills)

Two distinct surfaces use the local `codex exec` CLI for different audiences:

**Skills (run-time, user-task)**: when a Skill spawns Codex as part of executing a user's task (e.g. `/devlyn:auto-resolve` calling Codex BUILD), follow the wrapper-form contract in `config/skills/_shared/engine-routing.md` and `_shared/codex-config.md`. Decision-mode taxonomy (`solo` / `pair_critic` / `pair_consensus`) lives in `autoresearch/NORTH-STAR.md` and lands as policy in iter-0020. Until then, skill-level pair patterns (CRITIC = Codex critiques Claude, etc.) are the legacy shape.

**Autoresearch loop (change-time, harness developer)**: when *we* (the developer or the iteration loop) consult Codex for cross-model review of a harness change — design verdicts, hypothesis pre-checks, PR-style audits — use the companion wrapper:

```bash
bash config/skills/_shared/codex-monitored.sh \
  -C /Users/aipalm/Documents/GitHub/devlyn-cli \
  -s read-only \
  -c model_reasoning_effort=xhigh \
  "<your prompt>"
```

Pattern (per `feedback_codex_cross_check.md` + `feedback_user_directions_vs_debate.md`):

1. **Reason independently first.** Form your own verdict with concrete evidence (file paths, line numbers, raw data, expected vs actual). Never delegate the decision.
2. **Send Codex rich evidence**, not "what should I do?" prompts. Include your draft conclusion and ask for falsification — Codex acts as a GAN critic.
3. **Surface Codex pushback transparently.** When Codex disagrees, present both views to the user; do not silently adopt either side. The user's direction is the final arbiter.
4. **Never pipe the wrapper output** (`| tail`, `| head`, `| grep` without `--line-buffered`). The wrapper refuses pipe-stdout per iter-0009 to prevent byte-watchdog starvation. Read the persisted output file the wrapper writes when output is large.

This is "iteration-loop pair," distinct from "auto-resolve pair" — same vocabulary (`solo` / `pair_critic` / `pair_consensus`), different thresholds. Iteration-loop pair is human-supervised meta-work; the cost is amortized over harness improvements that affect every future run, so pair freely on non-trivial changes. Auto-resolve pair is hands-free user-task execution; every pair call is paid by the user on every run, so it must be aggressively gated (iter-0020).

Where the cumulative companion-pair history lives: `autoresearch/HANDOFF.md` "Codex collaboration log (running)" — append-only, one line per round.

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

## Bare-Case Guardrail

The modal run — single spec, solo build, no browser, standard route, PASS on first EVAL, clean CRITIC, no fix loops — is the primary performance target. No new hot-path phase, no sub-skill delegation, and no instrumentation may land without an A/B proof that this case's wall-time and tokens do not regress. Complex cases may cost more; the bare case may not.

## Communication Style

Lead with **objective data** (popularity, benchmarks, community adoption) before opinions — especially when the user asks "what's popular" or "what do others use."

## Commit Conventions

Follow `.claude/commit-conventions.md`.

## Design System

When doing UI/UX work, follow `docs/design-system.md` if it exists.
