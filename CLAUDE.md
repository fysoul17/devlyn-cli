# Project Instructions

## General

- Proactively use subagents and skills where needed
- Follow commit conventions in `.claude/commit-conventions.md`
- Follow design system in `docs/design-system.md` for UI/UX work if exist

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

For complex investigations, use `/investigate` skill or spawn parallel Task agents to explore different areas simultaneously.

## Feature Development

1. **Plan first** - Always output a concrete implementation plan with specific file changes before writing code
2. **Track progress** - Use TodoWrite to checkpoint each phase
3. **Test validation** - Write tests alongside implementation; iterate until green
4. **Small commits** - Commit working increments rather than large changesets

For complex features, use the Plan agent to design the approach before implementation.

## Debugging Workflow

Use `/devlyn.resolve` for systematic bug fixing with test-driven validation.

## Communication Style

- Lead with **objective data** (popularity, benchmarks, community adoption) before personal opinions
- When user asks "what's popular" or "what do others use", provide data-driven answers
- Keep recommendations actionable and specific
