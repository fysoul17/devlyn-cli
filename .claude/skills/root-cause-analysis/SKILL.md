# Root Cause Analysis

Standard methodology for investigating bugs, issues, and unexpected behavior. Apply this framework whenever diagnosing a problem.

## Trigger

- User reports a bug or unexpected behavior
- Error logs or stack traces need diagnosis
- "Why does X happen?" or "What's causing X?" questions
- Debugging sessions
- Any use of `/devlyn.resolve` or `/devlyn.team-resolve`

## 5 Whys Protocol

For every issue, trace from symptom to root cause:

**Why 1**: Why did [symptom] happen?
→ Because [cause 1]. Evidence: [file:line]

**Why 2**: Why did [cause 1] happen?
→ Because [cause 2]. Evidence: [file:line]

**Why 3**: Why did [cause 2] happen?
→ Because [cause 3]. Evidence: [file:line]

Continue until you reach something **actionable** — a code change that prevents the entire chain.

### Stop Criteria
- You've reached a design decision or architectural choice that caused the issue
- You've found a missing validation, wrong assumption, or incorrect logic
- Further "whys" leave the codebase (external dependency, infrastructure)

**NEVER stop at "the code does X"** — always ask WHY the code does X.

## Evidence Standards

Every claim MUST reference a specific `file:line`. No speculation about code you haven't read.

1. Read the actual code before forming hypotheses
2. Trace the execution path: entry → intermediate calls → issue location
3. Check git blame for when/why the problematic code was introduced
4. Find related tests that cover (or miss) the affected area
5. Generate 2-3 hypotheses, each with supporting evidence

## No-Workaround Rule

Every fix MUST address the root cause. Stop immediately if you catch yourself:

- Adding `|| defaultValue` to mask null/undefined
- Adding `try/catch` that swallows errors silently
- Using `?.` to skip over null when null IS the bug
- Hard-coding a value for the specific failing case
- Adding a "just in case" check that shouldn't be needed
- Suppressing warnings/errors instead of fixing them
- Adding retry logic instead of fixing why it fails

If the real fix requires significant refactoring, present the scope to the user — never ship a workaround "for now".

## Test-Driven Validation

1. Write a failing test that reproduces the issue
2. Implement the fix
3. Run the test — if it still fails, **revert completely** and try the next hypothesis
4. Never layer fixes on top of failed attempts
5. Run the full test suite for regressions

## Routing

- **Simple issue** (single file, obvious cause): Use `/devlyn.resolve`
- **Complex issue** (multi-module, unclear cause, security implications): Use `/devlyn.team-resolve` for multi-perspective investigation
