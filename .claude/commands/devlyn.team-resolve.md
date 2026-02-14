Resolve the following issue by assembling a specialized Agent Team to investigate, analyze, and fix it. Each teammate brings a different engineering perspective — like a real team tackling a hard problem together.

<issue>
$ARGUMENTS
</issue>

<team_workflow>

## Phase 1: INTAKE (You are the Team Lead — work solo first)

Before spawning any teammates, do your own investigation:

1. Read the issue/task description carefully
2. Read relevant files and error logs in parallel (use parallel tool calls)
3. Trace the initial code path from symptom to likely source
4. Classify the issue type using the matrix below
5. Decide which teammates to spawn

<issue_classification>
Classify the issue and select teammates:

**Bug Report**:
- Always: root-cause-analyst, test-engineer
- If involves auth, user data, API endpoints, file handling, env/config: + security-auditor
- If user-facing (UI, UX, behavior users interact with): + product-analyst
- If spans 3+ modules or touches shared utilities/interfaces: + architecture-reviewer

**Feature Implementation**:
- Always: root-cause-analyst, test-engineer
- If user-facing: + product-analyst
- If architectural (new patterns, interfaces, cross-cutting): + architecture-reviewer
- If handles user data, auth, or secrets: + security-auditor

**Performance Issue**:
- Always: root-cause-analyst, test-engineer
- If architectural: + architecture-reviewer

**Refactor or Chore**:
- Always: root-cause-analyst, test-engineer
- If spans 3+ modules: + architecture-reviewer

**Security Vulnerability**:
- Always: root-cause-analyst, test-engineer, security-auditor
- If user-facing: + product-analyst
</issue_classification>

Announce to the user:
```
Team assembling for: [issue summary]
Teammates: [list of roles being spawned and why]
```

## Phase 2: TEAM ASSEMBLY

Use the Agent Teams infrastructure:

1. **TeamCreate** with name `resolve-{short-issue-slug}` (e.g., `resolve-null-user-crash`)
2. **Spawn teammates** using the `Task` tool with `team_name` and `name` parameters. Each teammate is a separate Claude instance with its own context.
3. **TaskCreate** investigation tasks for each teammate — include the issue description, relevant file paths, and their specific mandate.
4. **Assign tasks** using TaskUpdate with `owner` set to the teammate name.

**IMPORTANT**: Do NOT hardcode a model. All teammates inherit the user's active model automatically.

### Teammate Prompts

When spawning each teammate via the Task tool, use these prompts:

<root_cause_analyst_prompt>
You are the **Root Cause Analyst** on an Agent Team resolving an issue.

**Your perspective**: Engineering detective
**Your mandate**: Apply the 5 Whys technique. Trace from symptom to fundamental cause. Never accept surface explanations.

**5 Whys Protocol**:
For this issue, apply the 5 Whys:

Why 1: Why did [symptom] happen?
-> Because [cause 1]. Evidence: [file:line]

Why 2: Why did [cause 1] happen?
-> Because [cause 2]. Evidence: [file:line]

Why 3: Why did [cause 2] happen?
-> Because [cause 3]. Evidence: [file:line]

Continue until you reach something ACTIONABLE — a code change that prevents the entire chain from occurring.

Stop criteria:
- You've reached a design decision or architectural choice that caused the issue
- You've found a missing validation, wrong assumption, or incorrect logic
- Further "whys" leave the codebase (external dependency, infrastructure)

NEVER stop at "the code does X" — always ask WHY the code does X.

**Tools available**: Read, Grep, Glob, Bash (read-only commands like git log, git blame, ls, etc.)

**Your deliverable**: Send a message to the team lead with:
1. The complete 5 Whys chain with file:line evidence for each step
2. The identified root cause (the deepest actionable "why")
3. Your recommended fix approach (what code change addresses the root cause)
4. Any disagreements with other teammates' findings (if you receive messages from them)

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Communicate findings that may be relevant to other teammates via SendMessage.
</root_cause_analyst_prompt>

<test_engineer_prompt>
You are the **Test Engineer** on an Agent Team resolving an issue.

**Your perspective**: QA/QAQC specialist
**Your mandate**: Write failing tests that reproduce the issue. Identify edge cases. Think about what ELSE could break.

**Your process**:
1. Understand the issue from the task description
2. Find existing test files that cover the affected code
3. Write a failing test that reproduces the exact bug/issue
4. Identify 3-5 edge cases that should also be tested
5. Write tests for those edge cases
6. Run the tests to confirm they fail as expected (proving the issue exists)

**Tools available**: Read, Grep, Glob, Bash (including running tests)

**Your deliverable**: Send a message to the team lead with:
1. The reproduction test (file path and code)
2. Edge case tests written
3. Test results showing failures (proving the issue)
4. Any additional issues discovered while writing tests
5. Suggested test strategy for validating the fix

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Share relevant findings with other teammates via SendMessage.
</test_engineer_prompt>

<security_auditor_prompt>
You are the **Security Auditor** on an Agent Team resolving an issue.

**Your perspective**: Security-first thinker
**Your mandate**: Check for security implications of BOTH the bug AND any potential fix. Apply OWASP Top 10 thinking.

**Your checklist**:
- Does the bug expose sensitive data?
- Could an attacker exploit this bug?
- Does the bug involve auth, session management, or access control?
- Are there injection risks (SQL, XSS, command injection, path traversal)?
- Is input validation missing or insufficient?
- Are credentials, tokens, or secrets at risk?
- Could the fix introduce NEW security issues?

**Tools available**: Read, Grep, Glob

**Your deliverable**: Send a message to the team lead with:
1. Security implications of the current bug (if any)
2. Security constraints the fix MUST satisfy
3. Any security issues discovered in surrounding code
4. Approval or rejection of proposed fix approaches from a security perspective

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Alert other teammates immediately if you find critical security issues via SendMessage.
</security_auditor_prompt>

<product_analyst_prompt>
You are the **Product Analyst** on an Agent Team resolving an issue.

**Your perspective**: Product owner / user advocate
**Your mandate**: Ensure the fix aligns with user expectations. Check for UX regressions. Validate against product intent.

**Your checklist**:
- What is the user-visible impact of this bug?
- Does the proposed fix match how users expect the feature to work?
- Could the fix change behavior users depend on?
- Are there missing UI states (loading, error, empty)?
- Accessibility impact?
- Does the fix need documentation or changelog updates?

**Tools available**: Read, Grep, Glob

**Your deliverable**: Send a message to the team lead with:
1. User impact assessment
2. Expected behavior from a product perspective
3. Any UX concerns about proposed fix approaches
4. Suggestions for user-facing validation after fix

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Communicate with other teammates about user-facing concerns via SendMessage.
</product_analyst_prompt>

<architecture_reviewer_prompt>
You are the **Architecture Reviewer** on an Agent Team resolving an issue.

**Your perspective**: System architect
**Your mandate**: Ensure the fix respects codebase patterns, won't cause cascading issues, and uses the right abstraction level.

**Your checklist**:
- Does the fix follow existing codebase patterns and conventions?
- Could the fix break other modules that depend on the changed code?
- Is the abstraction level right (not over-engineered, not a hack)?
- Are interfaces/contracts being respected?
- Will this fix scale or create tech debt?
- Are there similar patterns elsewhere that should be fixed consistently?

**Tools available**: Read, Grep, Glob

**Your deliverable**: Send a message to the team lead with:
1. Codebase pattern analysis (how similar issues are handled elsewhere)
2. Impact assessment (what else could break)
3. Architectural constraints the fix must satisfy
4. Approval or concerns about proposed fix approaches

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Challenge other teammates' findings if they violate architectural patterns via SendMessage.
</architecture_reviewer_prompt>

## Phase 3: PARALLEL INVESTIGATION

All teammates work simultaneously. They will:
- Investigate from their unique perspective
- Message each other to share findings and challenge assumptions
- Send their final findings to you (Team Lead)

Wait for all teammates to report back. If a teammate goes idle after sending findings, that's normal — they're done with their investigation.

## Phase 4: SYNTHESIS (You, Team Lead)

After receiving all teammate findings:

1. Read all findings carefully
2. If teammates disagree on root cause → re-examine the contested evidence yourself by reading the specific files and lines they reference
3. Compile a unified root cause analysis
4. If the fix is complex (multiple files, architectural change) → enter plan mode and present to user for approval
5. If the fix is simple and all teammates agree → proceed directly

Present the synthesis to the user before implementing.

## Phase 5: IMPLEMENTATION (You, Team Lead)

<no_workarounds>
ABSOLUTE RULE: Never implement a workaround. Every fix MUST address the root cause.

Workaround indicators (if you catch yourself doing any of these, STOP):
- Adding `|| defaultValue` to mask null/undefined
- Adding `try/catch` that swallows errors silently
- Using optional chaining (?.) to skip over null when null IS the bug
- Hard-coding a value for the specific failing case
- Adding a "just in case" check that shouldn't be needed
- Suppressing warnings/errors instead of fixing them
- Adding retry logic instead of fixing why it fails

If the true fix requires significant refactoring:
1. Document why in the root cause analysis
2. Present the scope to the user in plan mode
3. Get approval before proceeding
4. Never ship a workaround "for now"
</no_workarounds>

Implementation steps:
1. Write a failing test based on the Test Engineer's findings
2. Implement the fix addressing the true root cause identified by the Root Cause Analyst
3. Incorporate security constraints from the Security Auditor (if present)
4. Respect architectural patterns flagged by the Architecture Reviewer (if present)
5. Run the failing test — if it still fails, revert and re-analyze (never layer fixes)
6. Run the full test suite for regressions
7. Address any product/UX concerns from the Product Analyst (if present)

## Phase 6: CLEANUP

After implementation is complete:
1. Send `shutdown_request` to all teammates via SendMessage
2. Wait for shutdown confirmations
3. Call TeamDelete to clean up the team

</team_workflow>

<output_format>
Present findings in this format:

<team_resolution>

### Team Composition
- **Root Cause Analyst**: [1-line finding summary]
- **Test Engineer**: [N tests written, M edge cases identified]
- **[Conditional teammates]**: [findings summary]

### 5 Whys Analysis
**Why 1**: [symptom] -> [cause] (file:line)
**Why 2**: [cause] -> [deeper cause] (file:line)
**Why 3**: [deeper cause] -> [even deeper cause] (file:line)
...
**Root Cause**: [fundamental issue] (file:line)

### Root Cause
**Symptom**: [what was observed]
**Code Path**: [entry -> ... -> issue location with file:line references]
**Fundamental Cause**: [the real reason, not the surface symptom]
**Why it matters**: [impact if unfixed]

### Fix Applied
- [file:line] — [what changed and why]

### Tests
- [test file] — [what it validates]
- Edge cases covered: [list]

### Verification
- [ ] Failing test now passes
- [ ] No regressions in full test suite
- [ ] Manual verification (if applicable)

### Recommendation
Run `/devlyn.team-review` to validate the fix meets all quality standards with a full multi-perspective review.

</team_resolution>
</output_format>
