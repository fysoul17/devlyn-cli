# Investigation Skill

Use this skill for code investigation, feature gap analysis, or understanding existing functionality.

## Trigger

- User asks to investigate, analyze, or understand code
- Feature gap analysis requests
- "How does X work?" questions
- Code exploration tasks

## Workflow

### Phase 1: Define Scope
Before starting, clarify:
- What specific question needs answering?
- What does "complete" look like for this investigation?
- Are there time constraints?

### Phase 2: Parallel Exploration
Spawn Task agents to explore different areas simultaneously:
```
Use Task tool to spawn parallel agents:
1. Agent for data layer analysis
2. Agent for API/service layer
3. Agent for UI/component layer
```

### Phase 3: Checkpoint Progress
Every significant finding, use TodoWrite to record:
- Files examined
- Patterns discovered
- Questions raised
- Hypotheses formed

### Phase 4: Synthesize & Report
ALWAYS output a structured summary before ending:

```markdown
## Investigation Summary: [Topic]

### Files Examined
- `path/to/file.ts` - [what it does]
- `path/to/other.ts` - [what it does]

### Key Findings
1. [Finding with file:line reference]
2. [Finding with file:line reference]

### Architecture/Flow
[Brief description or diagram of how components interact]

### Gaps/Issues Identified
- [ ] Gap 1
- [ ] Gap 2

### Remaining Unknowns
- Question that needs more investigation

### Recommended Next Steps
1. Actionable step
2. Actionable step
```

## Rules

- NEVER end mid-investigation without a summary
- ALWAYS provide file:line references for findings
- Use TodoWrite to checkpoint progress every 5-10 minutes
- If interrupted, output whatever findings exist so far
- Prefer parallel Task agents for large codebases
