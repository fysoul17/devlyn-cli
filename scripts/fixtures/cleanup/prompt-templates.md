# Prompt Templates

Reusable prompts optimized for common workflows based on usage patterns.

## Investigation with Checkpoints

Use for code investigation or feature analysis to ensure findings are captured:

```
Investigate [issue/feature]. As you go, use TodoWrite to checkpoint your findings.
Every 5-10 minutes of analysis, output a 'Current Understanding' summary so I have
something actionable if we need to stop.
```

## Time-Boxed Sessions

Use when you have limited time and need guaranteed deliverables:

```
I have [X] minutes. My goal is [specific goal]. Success means [specific deliverable].
Start with the minimum viable solution, then improve if time allows.
```

## Debugging

For systematic debugging, use `/devlyn.resolve [issue description]` which includes:
- Code path mapping
- Hypothesis-driven analysis
- Test-driven fix validation
- Full regression check

## Parallel Feature Analysis

Use for comprehensive feature gap analysis:

```
Spawn separate agents to:
(1) analyze the data layer for this feature
(2) check the API endpoints
(3) review the UI components
Consolidate findings into a single summary.
```

## Autonomous Feature Implementation

Use for end-to-end feature implementation with validation:

```
Implement [feature] end-to-end. First, use Task to spawn a sub-agent to analyze
existing patterns in the codebase. Then implement the feature with:
1) [Component 1]
2) [Component 2]
3) [Component 3]
Write comprehensive tests and iterate on the implementation until all tests pass.
Run the full test suite before presenting the final diff. Do not stop until you
have working, tested code ready for PR.
```

## Autonomous Bug Fix

For complex bugs that need autonomous resolution:

```
/devlyn.resolve [bug description]

After analysis, implement the fix autonomously:
- Write failing test first
- Iterate through hypotheses until test passes
- Run full test suite before completing
- Do not stop at 'needs more investigation'
```
