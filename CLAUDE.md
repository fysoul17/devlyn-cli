# Project Instructions

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
2. **Checkpoint progress** - Use TodoWrite every 5-10 minutes to save findings
3. **Output intermediate summaries** - Provide "Current Understanding" snapshots so work isn't lost if interrupted
4. **Always deliver findings** - Never end mid-analysis; at minimum output:
   - Files examined
   - Key findings
   - Remaining unknowns
   - Recommended next steps

For complex investigations, use `/devlyn:team-resolve` to assemble a multi-perspective investigation team, or spawn parallel Task agents to explore different areas simultaneously.

## UI/UX Workflow

The full design-to-implementation pipeline:

1. `/devlyn:design-ui` → Generate 5 style explorations
2. `/devlyn:design-system [N]` → Extract tokens from chosen style
3. `/devlyn:implement-ui` → Team implements or improves UI from design system
4. `/devlyn:team-resolve [feature]` → Add features on top

## Feature Development

1. **Plan first** - Always output a concrete implementation plan with specific file changes before writing code
2. **Track progress** - Use TodoWrite to checkpoint each phase
3. **Test validation** - Write tests alongside implementation; iterate until green
4. **Small commits** - Commit working increments rather than large changesets

For complex features, use the Plan agent to design the approach before implementation.

## Automated Pipeline (Recommended Starting Point)

For hands-free build-evaluate-polish cycles — works for bugs, features, refactors, and chores:

```
/devlyn:auto-resolve [task description]
```

This runs the full pipeline automatically: **Build → Browser Validate → Evaluate → Fix Loop → Simplify → Review → Security Review → Clean → Docs**. Each phase runs as a separate subagent with its own context. Communication between phases happens via files (`.devlyn/done-criteria.md`, `.devlyn/EVAL-FINDINGS.md`, `.devlyn/BROWSER-RESULTS.md`).

For web projects, the Browser Validate phase starts the dev server and tests the implemented feature in a real browser — clicking buttons, filling forms, verifying results. If the feature doesn't work, findings feed back into the fix loop.

Optional flags:
- `--max-rounds 3` — increase max evaluate-fix iterations (default: 2)
- `--skip-browser` — skip browser validation phase (auto-skipped for non-web changes)
- `--skip-review` — skip team-review phase
- `--skip-clean` — skip clean phase
- `--skip-docs` — skip update-docs phase
- `--with-codex [evaluate|review|both]` — use OpenAI Codex as cross-model evaluator/reviewer (requires codex-mcp-server)

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

When a conversation approaches context limits (50k+ tokens):
1. Check usage with `/context`
2. Create a HANDOFF.md summarizing: what was attempted, what succeeded, what failed, and next steps
3. Start a new session with `/clear`
4. Load context: `@HANDOFF.md Read this file and continue the work`

## Communication Style

- Lead with **objective data** (popularity, benchmarks, community adoption) before personal opinions
- When user asks "what's popular" or "what do others use", provide data-driven answers
- Keep recommendations actionable and specific
