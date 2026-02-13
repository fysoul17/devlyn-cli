# Feature Gap Analysis Skill

Use this skill to systematically identify missing features and functionality gaps in the codebase.

## Trigger

- "What features are missing?"
- "Analyze gaps in [feature area]"
- Feature comparison requests
- "What should we build next?"

## Workflow

### Phase 1: Define Scope
1. Identify the feature area to analyze
2. Establish comparison baseline (competitor, spec, user needs)
3. Define what "complete" means for this analysis

### Phase 2: Parallel Analysis
Spawn Task agents to investigate simultaneously:

```markdown
Agent 1: Current State Analysis
- What exists today?
- How is it implemented?
- What are its limitations?

Agent 2: Standard/Competitor Analysis
- What do similar products offer?
- What's the industry standard?
- What do users expect?

Agent 3: User-Facing Gaps
- What's missing from user perspective?
- What are common complaints/requests?
- What workflows are incomplete?

Agent 4: Technical Debt
- What technical limitations block features?
- What refactoring would enable new capabilities?
- What dependencies are outdated?
```

### Phase 3: Synthesize Findings
Compile findings into prioritized analysis:

```markdown
## Feature Gap Analysis: [Area]

### Current State
| Feature | Status | Implementation | Notes |
|---------|--------|----------------|-------|
| Feature A | Complete | `path/to/file.ts` | |
| Feature B | Partial | `path/to/file.ts` | Missing X |
| Feature C | Missing | - | Needed for Y |

### Gap Prioritization

#### High Priority (User Impact + Feasibility)
1. **[Gap]**
   - Impact: [Why it matters]
   - Complexity: S/M/L
   - Dependencies: [What's needed first]
   - Suggested approach: [Brief technical direction]

#### Medium Priority
2. **[Gap]**
   - ...

#### Low Priority / Nice-to-Have
3. **[Gap]**
   - ...

### Technical Debt Blocking Progress
- [ ] Debt item 1 - blocks [features]
- [ ] Debt item 2 - blocks [features]

### Recommended Roadmap
1. Phase 1: [Quick wins]
2. Phase 2: [Core features]
3. Phase 3: [Advanced features]
```

### Phase 4: Generate Implementation Plans
For top priority gaps, draft initial implementation plans:

```markdown
## Implementation Plan: [Top Gap]

### Files to Create/Modify
- `new/file.ts` - [purpose]
- `existing/file.ts` - [changes needed]

### Key Decisions Needed
- Decision 1: Option A vs Option B
- Decision 2: ...

### Draft Implementation Steps
1. Step 1
2. Step 2
3. ...
```

## Rules

- ALWAYS output prioritized, actionable findings
- Include complexity estimates (S/M/L) for each gap
- Provide file:line references to existing implementations
- Don't just list gaps - provide implementation direction
- Use TodoWrite to checkpoint analysis progress
- If interrupted, output whatever analysis exists so far
