# Project Instructions

## Quick Start

For most work, the recommended sequence is:

1. `/devlyn:ideate` — turn an idea into roadmap-ready specs
2. `/devlyn:auto-resolve "Implement per spec at docs/roadmap/phase-N/X-name.md"` — hands-free build → evaluate → polish
3. `/devlyn:preflight` — verify the implementation matches the roadmap before shipping

All three default to `--engine auto`, which routes each phase to the optimal model (Codex GPT-5.4 for hard coding, Claude Opus 4.7 for evaluation/critique). The cross-model GAN dynamic — different models build vs critique — catches what single-model pipelines miss.

## General

- Proactively use subagents and skills where needed
- Follow commit conventions in `.claude/commit-conventions.md`
- Follow design system in `docs/design-system.md` for UI/UX work if exist

## Error Handling Philosophy

**No silent fallbacks.** Handle errors explicitly and show the user what happened.

- **Default behavior**: When something fails, display a clear error state in the UI (error message, retry option, or actionable guidance). Do NOT silently fall back to default/placeholder data.
- **Fallbacks are the exception, not the rule.** Only use fallbacks when it is a widely accepted best practice (e.g., fallback fonts in CSS, CDN failover, graceful image loading with placeholder). If unsure, handle the error explicitly instead.
- **Never hide failures.** The user should always know when something went wrong. A visible error with a retry button is better UX than silently showing stale/default data.
- **Pattern**: `try { doThing() } catch (error) { showErrorUI(error) }` — NOT `try { doThing() } catch { return fallbackValue }`

## Investigation Workflow

When investigating bugs, analyzing features, or exploring code:

1. **Define exit criteria upfront** - Ask "What does 'done' look like?" before starting
2. **Checkpoint progress** - Use the task tools (TaskCreate / TaskUpdate) every 5-10 minutes to save findings
3. **Output intermediate summaries** - Provide "Current Understanding" snapshots so work isn't lost if interrupted
4. **Always deliver findings** - Never end mid-analysis; at minimum output:
   - Files examined
   - Key findings
   - Remaining unknowns
   - Recommended next steps

For complex investigations, use `/devlyn:team-resolve` to assemble a multi-perspective investigation team, or spawn parallel Agent subagents to explore different areas simultaneously.

## UI/UX Workflow

The full design-to-implementation pipeline:

1. `/devlyn:design-ui` → Generate 5 style explorations
2. `/devlyn:design-system [N]` → Extract tokens from chosen style
3. `/devlyn:implement-ui` → Team implements or improves UI from design system
4. `/devlyn:team-resolve [feature]` → Add features on top

## Feature Development

1. **Plan first** - Always output a concrete implementation plan with specific file changes before writing code
2. **Track progress** - Use the task tools (TaskCreate / TaskUpdate) to checkpoint each phase
3. **Test validation** - Write tests alongside implementation; iterate until green
4. **Small commits** - Commit working increments rather than large changesets

For complex features, spawn the `Plan` subagent (`Agent` tool with `subagent_type: "Plan"`) to design the approach before implementation.

## Automated Pipeline (Recommended Starting Point)

For hands-free build-evaluate-polish cycles — works for bugs, features, refactors, and chores:

```
/devlyn:auto-resolve [task description]
```

This runs the full pipeline automatically: **Build → Build Gate → Browser Validate → Evaluate → Fix Loop → Simplify → Review → Challenge → Security Review → Clean → Docs**. Each phase runs as a separate subagent with its own context. Communication between phases happens via files (`.devlyn/done-criteria.md`, `.devlyn/BUILD-GATE.md`, `.devlyn/EVAL-FINDINGS.md`, `.devlyn/BROWSER-RESULTS.md`, `.devlyn/CHALLENGE-FINDINGS.md`).

The **Build Gate** (Phase 1.4) runs real compilers, typecheckers, and linters — the same commands CI/Docker/production will run. It auto-detects project types (Next.js, Rust, Go, Solidity, Expo, Swift, etc.) and Dockerfiles. This is the primary defense against "tests pass locally, breaks in CI/Docker" class of bugs (type errors in un-tested files, cross-package drift, Dockerfile copy mismatches).

The **Challenge** phase (Phase 4.5) is a fresh skeptical review with no checklist — a subagent reads the entire diff cold with zero context from prior phases and asks "would I ship this to production with my name on it?" This catches the subtle issues that structured checklist-driven reviews miss: wrong-but-working approaches, unstated assumptions, non-idiomatic patterns, and integration gaps.

For web projects, the Browser Validate phase starts the dev server and tests the implemented feature in a real browser — clicking buttons, filling forms, verifying results. If the feature doesn't work, findings feed back into the fix loop.

Optional flags:
- `--max-rounds 6` — increase max evaluate-fix iterations (default: 4)
- `--skip-browser` — skip browser validation phase (auto-skipped for non-web changes)
- `--skip-build-gate` — skip the deterministic build gate (not recommended)
- `--build-gate strict` — treat warnings as errors; `--build-gate no-docker` — skip Docker builds for speed
- `--skip-review` — skip team-review phase
- `--skip-clean` — skip clean phase
- `--skip-docs` — skip update-docs phase
- `--engine auto|codex|claude` — intelligent model routing. `auto` (default) routes each phase and team role to the optimal model based on benchmark data: Codex GPT-5.4 handles BUILD and FIX (SWE-bench Pro lead), Claude Opus 4.7 handles EVALUATE and CHALLENGE (long-context retrieval + skeptical reasoning). Different models build vs critique — the cross-model GAN dynamic catches what single-model pipelines miss. `codex` forces Codex for implementation, Claude for orchestration and Chrome MCP. `claude` uses Claude for everything. Requires codex-mcp-server for `auto` and `codex` modes.

## Preflight Check (Post-Roadmap Verification)

After completing a roadmap (or a phase), verify that everything was actually implemented correctly:

```
/devlyn:preflight
```

This reads every commitment from VISION.md, ROADMAP.md, and item specs, then audits the codebase evidence-based. The code auditor now runs real build/typecheck commands as its first step — any project that doesn't compile is flagged as BROKEN at CRITICAL severity before individual commitments are even checked. Also checks in the browser for web projects.

Output: `.devlyn/PREFLIGHT-REPORT.md` with categorized findings (MISSING, INCOMPLETE, DIVERGENT, BROKEN, STALE_DOC). Confirmed gaps can be promoted to new roadmap items for auto-resolve.

Optional flags:
- `--phase N` — audit only phase N items
- `--autofix` — auto-promote CRITICAL/HIGH findings and run auto-resolve
- `--skip-browser` — skip browser validation
- `--skip-docs` — skip documentation audit
- `--engine auto|codex|claude` — `auto` (default) routes the code-auditor to Codex (SWE-bench Pro +11.7pp on code analysis); the docs-auditor and browser-auditor always use Claude regardless of `--engine` (writing-quality strength on docs drift; Chrome MCP tools are session-bound to Claude Code)

**Recommended workflow**: `/devlyn:ideate` → `/devlyn:auto-resolve` (repeat) → `/devlyn:preflight` → fix gaps → `/devlyn:preflight` (verify)

## Manual Pipeline (Step-by-Step Control)

When you want to run each step yourself with review between phases:

1. `/devlyn:team-resolve [issue]` → Investigate + implement (writes `.devlyn/done-criteria.md`)
2. `/devlyn:evaluate` → Grade against done-criteria (writes `.devlyn/EVAL-FINDINGS.md`)
3. If findings exist: `/devlyn:team-resolve "Fix issues in .devlyn/EVAL-FINDINGS.md"` → Fix loop
4. `/simplify` → Quick cleanup pass
5. `/devlyn:team-review` → Multi-perspective team review (for important PRs)
6. `/devlyn:clean` → Codebase hygiene
7. `/devlyn:update-docs` → Keep docs in sync

Steps 5-7 are optional depending on scope.

## Vibe Coding Workflow

The recommended sequence after writing code:

1. **Write code** (vibe coding)
2. `/simplify` → Quick cleanup pass (reuse, quality, efficiency)
3. `/devlyn:review` → Thorough solo review with security-first checklist
4. `/devlyn:team-review` → Multi-perspective team review (for important PRs)
5. `/devlyn:clean` → Periodic codebase-wide hygiene
6. `/devlyn:update-docs` → Keep docs in sync

Steps 4-6 are optional depending on the scope of changes. `/simplify` should always run before `/devlyn:review` to catch low-hanging fruit cheaply.

## Documentation Workflow

- **Sync docs with codebase**: Use `/devlyn:update-docs` to clean up stale content, update outdated info, and generate missing docs
- **Focused doc update**: Use `/devlyn:update-docs [area]` for targeted updates (e.g., "API reference", "getting-started")
- Preserves all forward-looking content: roadmaps, future plans, visions, open questions
- If no docs exist, proposes a tailored docs structure and generates initial content

## Browser Testing Workflow

- **Standalone**: Use `/devlyn:browser-validate` to test any web feature in the browser — starts the dev server, tests the feature end-to-end, fixes issues it finds
- **In pipeline**: Auto-resolve includes browser validation automatically for web projects (between Build and Evaluate phases)
- **Tiered**: Uses chrome MCP tools if available, falls back to Playwright, then curl
- **Feature-first**: Tests the implemented feature (from done-criteria), not just "does the page load"

## Debugging Workflow

- **Simple bugs**: Use `/devlyn:resolve` for systematic bug fixing with test-driven validation
- **Complex bugs**: Use `/devlyn:team-resolve` for multi-perspective investigation with a full agent team
- **Hands-free**: Use `/devlyn:auto-resolve` for fully automated resolve → evaluate → fix → polish pipeline
- **Post-fix review**: Use `/devlyn:team-review` for thorough multi-reviewer validation

## Maintenance Workflow

- **Codebase cleanup**: Use `/devlyn:clean` to detect and remove dead code, unused dependencies, complexity hotspots, and tech debt
- **Focused cleanup**: Use `/devlyn:clean [category]` for targeted sweeps (dead code, deps, tests, complexity, hygiene)
- **Periodic maintenance sequence**: `/devlyn:clean` → `/simplify` → `/devlyn:update-docs` → `/devlyn:review`

## Context Window Management

Claude 4.5 / 4.6 / 4.7 models auto-compact the conversation as it approaches the context limit, so you can keep working indefinitely without manual handoffs in most cases. Don't stop early due to token-budget concerns — the model continues from where it left off after compaction.

For genuinely multi-context-window work (e.g., a roadmap with many phases), persist state to disk so the next instance can resume:
- All `auto-resolve` and `preflight` runs already write durable state to `.devlyn/*.md` (done-criteria, BUILD-GATE, EVAL-FINDINGS, BROWSER-RESULTS, CHALLENGE-FINDINGS, PREFLIGHT-REPORT) and to git commits — pick up by reading those files plus `git log`.
- For long investigations, write progress notes to a `HANDOFF.md` and resume with `@HANDOFF.md continue from where this left off` if you need a fresh window.

Manually clearing with `/clear` is rarely necessary — only do it when context is genuinely irrelevant to the next task.

## Communication Style

- Lead with **objective data** (popularity, benchmarks, community adoption) before personal opinions
- When user asks "what's popular" or "what do others use", provide data-driven answers
- Keep recommendations actionable and specific
