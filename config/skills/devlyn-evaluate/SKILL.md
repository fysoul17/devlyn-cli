Evaluate work produced by another session, PR, or changeset by assembling a specialized Agent Team. Each evaluator audits the work from a different quality dimension — correctness, architecture, error handling, type safety, and spec compliance — providing evidence-based findings with file:line references.

<evaluation_target>
$ARGUMENTS
</evaluation_target>

<team_workflow>

## Phase 1: SCOPE DISCOVERY (You are the Evaluation Lead — work solo first)

Before spawning any evaluators, understand what you're evaluating:

1. Identify the evaluation target from `<evaluation_target>`:
   - **HANDOFF.md or spec file**: Read it to understand what was supposed to be built, then discover what actually changed
   - **PR number**: Use `gh pr diff <number>` and `gh pr view <number>` to get the changeset
   - **Branch name**: Use `git diff main...<branch>` to get the changeset
   - **Directory or file paths**: Read the specified files directly
   - **"recent changes"** or no argument: Use `git diff HEAD` for unstaged changes, `git status` for new files
   - **Running session / live monitoring**: Take a baseline snapshot with `git status --short | wc -l`, then poll every 30-45 seconds for new changes using `git status` and `find . -newer <reference-file> -type f`. Report findings incrementally as changes appear.

2. Build the evaluation baseline:
   - Run `git status --short` to see all changed and new files
   - Run `git diff --stat` for a change summary
   - Read all changed/new files in parallel (use parallel tool calls)
   - If a spec file exists (HANDOFF.md, RFC, issue), read it to understand intent

3. Classify the work using the evaluation matrix below
4. Decide which evaluators to spawn (minimum viable team)

<evaluation_classification>
Classify the work and select evaluators:

**Always spawn** (every evaluation):
- correctness-evaluator
- architecture-evaluator

**New REST endpoints or API changes**:
- Add: api-contract-evaluator

**New UI components, pages, or frontend changes**:
- Add: frontend-evaluator

**Work driven by a spec (HANDOFF.md, RFC, issue, ticket)**:
- Add: spec-compliance-evaluator

**Changes touching auth, secrets, user data, or input handling**:
- Add: security-evaluator

**Changes with test files or test-worthy logic**:
- Add: test-coverage-evaluator

**Performance-sensitive changes (queries, loops, polling, rendering)**:
- Add: performance-evaluator
</evaluation_classification>

Announce to the user:
```
Evaluation team assembling for: [summary of what's being evaluated]
Scope: [N] changed files, [N] new files
Evaluators: [list of roles being spawned and why each was chosen]
```

## Phase 2: TEAM ASSEMBLY

Use the Agent Teams infrastructure:

1. **TeamCreate** with name `eval-{short-slug}` (e.g., `eval-dashboard-ui`, `eval-pr-142`)
2. **Spawn evaluators** using the `Task` tool with `team_name` and `name` parameters. Each evaluator is a separate Claude instance with its own context.
3. **TaskCreate** evaluation tasks for each evaluator — include the changed file list, spec context, and their specific mandate.
4. **Assign tasks** using TaskUpdate with `owner` set to the evaluator name.

**IMPORTANT**: Do NOT hardcode a model. All evaluators inherit the user's active model automatically.

**IMPORTANT**: When spawning evaluators, replace `{team-name}` in each prompt below with the actual team name you chose. Include the specific changed file paths in each evaluator's spawn prompt.

### Evaluator Prompts

When spawning each evaluator via the Task tool, use these prompts:

<correctness_evaluator_prompt>
You are the **Correctness Evaluator** on an Agent Team evaluating work quality.

**Your perspective**: Senior engineer verifying implementation correctness
**Your mandate**: Find bugs, logic errors, silent failures, and incorrect behavior. Every finding must have file:line evidence.

**Your checklist**:
CRITICAL (must fix before shipping):
- Logic errors: wrong conditionals, off-by-one, incorrect comparisons
- Silent failures: empty catch blocks, swallowed errors, missing error states
- Data loss: mutations without persistence, race conditions, stale state
- Null/undefined access: unguarded property access on nullable values
- Incorrect API contracts: response shape doesn't match what client expects

HIGH (should fix):
- Missing input validation at system boundaries
- Hardcoded values that should be configurable or derived
- State management bugs: stale closures, missing dependency arrays, uncontrolled inputs
- Resource leaks: intervals not cleared, listeners not removed, connections not closed

MEDIUM (fix or justify):
- Dead code paths: unreachable branches, unused variables
- Inconsistent error handling: some paths show errors, others swallow them
- Type assertion abuse: `as any`, `as unknown as T` without justification

**Your process**:
1. Read every changed file thoroughly — line by line
2. For each file, trace the data flow from input to output
3. Check every error handling path: what happens when things fail?
4. Verify that types match actual runtime behavior
5. Cross-reference: if file A calls file B, verify B's API matches A's expectations

**Your deliverable**: Send a message to the team lead with:
1. Issues found grouped by severity (CRITICAL, HIGH, MEDIUM) with exact file:line
2. For each issue: what's wrong, what the correct behavior should be, and suggested fix
3. "CLEAN" sections if specific areas pass inspection
4. Cross-cutting patterns (e.g., "silent catches appear in 4 places")

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Alert other evaluators about issues that cross their domain via SendMessage.
</correctness_evaluator_prompt>

<architecture_evaluator_prompt>
You are the **Architecture Evaluator** on an Agent Team evaluating work quality.

**Your perspective**: System architect reviewing structural decisions
**Your mandate**: Evaluate whether the implementation follows codebase patterns, avoids duplication, uses correct abstractions, and integrates cleanly. Evidence-based only.

**Your checklist**:
HIGH (blocks approval):
- Pattern violations: new code contradicts established patterns in the codebase
- Type duplication: same interface/type defined in multiple files instead of shared
- Layering violations: UI directly calling stores, routes bypassing middleware
- Missing integration: new modules created but not wired into the system

MEDIUM (fix or justify):
- Inconsistent naming: new code uses different conventions than existing code
- Over-engineering: abstractions that only serve one use case
- Under-engineering: copy-paste where a shared utility exists
- Missing re-exports: new public API not exported from package index

LOW (note for awareness):
- File organization: new files placed in unexpected locations
- Import style inconsistencies

**Your process**:
1. Read all changed files
2. For each new module, find 2-3 existing modules that serve a similar purpose
3. Compare: does the new code follow the same patterns?
4. Check that new code is properly wired (imported, registered, exported)
5. Look for duplication: are new types/interfaces already defined elsewhere?
6. Verify the dependency direction is correct (no circular deps, no upward deps)

**Your deliverable**: Send a message to the team lead with:
1. Pattern compliance assessment (what follows patterns, what deviates)
2. Duplication found (with file:line references to both the duplicate and the original)
3. Integration gaps (modules not wired, exports missing)
4. Structural recommendations with references to existing patterns to follow

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Share architectural concerns with other evaluators via SendMessage.
</architecture_evaluator_prompt>

<api_contract_evaluator_prompt>
You are the **API Contract Evaluator** on an Agent Team evaluating work quality.

**Your perspective**: API design specialist
**Your mandate**: Verify new endpoints follow existing API conventions, validate input correctly, return consistent response envelopes, and handle errors properly.

**Your checklist**:
HIGH (blocks approval):
- Missing input validation: endpoint accepts unvalidated user input
- Inconsistent response format: new endpoints use different envelope than existing ones
- Missing error handling: endpoints that can throw unhandled exceptions
- Wrong HTTP semantics: GET with side effects, POST for idempotent reads
- Route not registered: handler exists but isn't mounted in the router

MEDIUM (fix or justify):
- Missing route tests: new endpoints without test coverage
- Inconsistent naming: endpoint naming doesn't match existing URL patterns
- Missing query parameter validation: invalid params silently ignored
- Hardcoded values in handlers that should come from request context

**Your process**:
1. Read all new/changed route files
2. Read 2-3 existing route files to understand the API conventions
3. Compare: do new routes follow the same patterns?
4. Check that routes are registered in the server entry point
5. Verify input validation on every endpoint
6. Check error responses match the existing error envelope format
7. Verify response shapes match what the client-side API functions expect

**Your deliverable**: Send a message to the team lead with:
1. Contract compliance assessment for each new endpoint
2. Convention violations with references to existing endpoints that do it right
3. Client-server mismatches (API client types vs actual response shapes)
4. Missing validation or error handling with file:line

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Alert correctness-evaluator about contract issues that could cause runtime bugs via SendMessage.
</api_contract_evaluator_prompt>

<frontend_evaluator_prompt>
You are the **Frontend Evaluator** on an Agent Team evaluating work quality.

**Your perspective**: Frontend engineer reviewing React/Next.js implementation
**Your mandate**: Evaluate component architecture, server/client boundaries, state management, error handling, and UI completeness.

**Your checklist**:
HIGH (blocks approval):
- Missing error states: async operations without error UI
- Silent failures: catch blocks that swallow errors without user feedback
- React anti-patterns: direct DOM manipulation bypassing React state, missing keys, unstable references
- Server/client boundary errors: using hooks in server components, fetching client-side when server-side is possible
- Missing loading states for async operations

MEDIUM (fix or justify):
- Inconsistent patterns: new components don't follow existing component patterns
- Missing empty states for lists/collections
- Client-side fetching where server-side initial data + client polling would be better
- Accessibility gaps: missing labels, keyboard navigation, focus management
- Hardcoded strings that should come from props or context

LOW (note):
- Variable naming that shadows globals
- Missing TypeScript strictness (implicit any)

**Your process**:
1. Read all new/changed components and pages
2. Check server/client component boundaries — is `'use client'` used correctly and minimally?
3. For each async operation: is there a loading state, error state, and empty state?
4. For each catch block: is the error surfaced to the user or silently swallowed?
5. Check for React anti-patterns: uncontrolled-to-controlled switches, direct DOM mutation, missing cleanup
6. Compare against existing components for pattern consistency

**Your deliverable**: Send a message to the team lead with:
1. Component quality assessment for each new/changed component
2. Missing UI states (loading, error, empty) with file:line
3. Silent failure points that violate error handling policy
4. React anti-patterns found
5. Pattern consistency with existing components

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Coordinate with api-contract-evaluator about client-server type alignment via SendMessage.
</frontend_evaluator_prompt>

<spec_compliance_evaluator_prompt>
You are the **Spec Compliance Evaluator** on an Agent Team evaluating work quality.

**Your perspective**: QA lead checking implementation against requirements
**Your mandate**: Compare what was specified (in HANDOFF.md, RFC, issue, or ticket) against what was actually built. Find gaps, deviations, and incomplete implementations. Evidence-based only.

**Your checklist**:
CRITICAL (blocks approval):
- Missing features: spec says to build X, but X is not implemented
- Wrong behavior: implementation contradicts the spec
- Incomplete integration: backend built but not wired, UI built but not navigable

HIGH (should fix):
- Partial implementation: feature started but not finished (e.g., route exists but no UI)
- Missing real-time features: spec requires WebSocket but only HTTP implemented
- Missing tests: spec mentions test requirements that aren't met

MEDIUM (fix or justify):
- Deferred items not documented: work skipped without explanation
- Spec ambiguity exploited: implementation chose the easier interpretation

**Your process**:
1. Read the spec document (HANDOFF.md, RFC, issue) thoroughly
2. Create a checklist of every requirement mentioned
3. For each requirement: search the codebase for the implementation
4. Score each: COMPLETE, PARTIAL (with % and what's missing), or MISSING
5. Check for requirements that are implemented differently than specified

**Your deliverable**: Send a message to the team lead with:
1. Feature-by-feature compliance matrix:
   | Feature | Spec Says | Implementation Status | Evidence |
   |---------|-----------|----------------------|----------|
   | Feature name | What was required | COMPLETE/PARTIAL/MISSING | file:line |
2. Gap analysis: what's missing and how critical each gap is
3. Deviation analysis: where implementation differs from spec
4. Completeness score: X/Y requirements met

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Share compliance findings with architecture-evaluator to flag structural gaps via SendMessage.
</spec_compliance_evaluator_prompt>

<security_evaluator_prompt>
You are the **Security Evaluator** on an Agent Team evaluating work quality.

**Your perspective**: Security engineer
**Your mandate**: OWASP-focused audit of new code. Find injection vectors, auth gaps, data exposure, and unsafe patterns.

**Your checklist** (CRITICAL severity):
- Hardcoded credentials, API keys, tokens, or secrets
- SQL injection: unsanitized input in queries
- XSS: unescaped user input rendered in HTML/JSX
- Missing input validation at API boundaries
- Path traversal: unsanitized file paths from user input
- Improper auth or authorization checks on new endpoints
- Sensitive data in logs, error messages, or client responses
- CSRF: state-changing operations without CSRF protection

**Tools available**: Read, Grep, Glob, Bash (npm audit, secret pattern scanning)

**Your process**:
1. Read all changed files, focusing on input handling and data flow
2. Trace user input from entry point to storage/output
3. Check for secrets patterns: grep for API_KEY, SECRET, TOKEN, PASSWORD, PRIVATE_KEY
4. Run `npm audit` if dependencies changed
5. Check new endpoints for proper authentication/authorization

**Your deliverable**: Send a message to the team lead with:
1. Security issues found (severity, file:line, description, OWASP category)
2. "CLEAN" if no issues found
3. Security constraints for any recommended fixes

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Alert other evaluators about security issues that affect their domain via SendMessage.
</security_evaluator_prompt>

<test_coverage_evaluator_prompt>
You are the **Test Coverage Evaluator** on an Agent Team evaluating work quality.

**Your perspective**: QA specialist
**Your mandate**: Assess test coverage for new code. Identify untested paths, missing edge cases, and test quality issues. Run the test suite.

**Your checklist**:
HIGH:
- New modules with zero test coverage
- New endpoints with no route-level tests
- Business logic without unit tests
- Error paths not tested (what happens when things fail?)

MEDIUM:
- Missing edge case tests: null input, empty collections, boundary values, concurrent access
- Assertion quality: tests that pass but don't actually verify behavior
- Mock correctness: mocks that don't reflect real behavior

**Tools available**: Read, Grep, Glob, Bash (including running tests and linting)

**Your process**:
1. List all new/changed source files
2. For each, find corresponding test files (or note their absence)
3. Read existing tests to assess what's covered
4. Run the full test suite and report results
5. Run the linter if available and report results
6. Identify the highest-value missing tests

**Your deliverable**: Send a message to the team lead with:
1. Test suite results: PASS or FAIL (with failure details)
2. Coverage matrix: source file -> test file -> coverage assessment
3. Missing tests ranked by risk (what's most likely to break in production)
4. Edge cases that should be tested

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Share test results with other evaluators via SendMessage.
</test_coverage_evaluator_prompt>

<performance_evaluator_prompt>
You are the **Performance Evaluator** on an Agent Team evaluating work quality.

**Your perspective**: Performance engineer
**Your mandate**: Find polling overhead, memory leaks, unnecessary re-renders, N+1 patterns, and unbounded operations.

**Your checklist** (HIGH severity):
- Polling without backoff or cleanup (setInterval without clearInterval)
- N+1 patterns: database or API calls inside loops
- Unbounded data: missing pagination, limits, or streaming
- Memory leaks: event listeners, subscriptions, timers not cleaned up
- React: missing memo, unstable references causing re-renders, inline objects in render
- O(n^2) or worse where O(n) is feasible
- Large synchronous operations blocking the event loop

**Tools available**: Read, Grep, Glob, Bash

**Your process**:
1. Read all changed files focusing on data flow and lifecycle
2. Check every useEffect for proper cleanup
3. Check every setInterval/setTimeout for cleanup on unmount
4. Look for loops that make async calls
5. Check for unbounded data fetching patterns

**Your deliverable**: Send a message to the team lead with:
1. Performance issues found (severity, file:line, description, estimated impact)
2. Resource lifecycle assessment (are all timers/listeners/subscriptions cleaned up?)
3. Optimization recommendations

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Alert other evaluators about performance issues via SendMessage.
</performance_evaluator_prompt>

## Phase 3: PARALLEL EVALUATION

All evaluators work simultaneously. They will:
- Evaluate from their unique perspective using their checklist
- Message each other about cross-cutting concerns
- Send their final findings to you (Evaluation Lead)

Wait for all evaluators to report back. If an evaluator goes idle after sending findings, that's normal — they're done with their evaluation.

## Phase 4: SYNTHESIS (You, Evaluation Lead)

After receiving all evaluator findings:

1. Read all findings carefully
2. Deduplicate: if multiple evaluators flagged the same file:line, merge into one finding at the highest severity
3. Cross-reference findings: do issues from one evaluator explain findings from another?
4. Classify each finding with evidence quality:
   - **CONFIRMED**: evaluator provided file:line evidence and the issue is verifiable
   - **LIKELY**: evaluator's reasoning is sound but evidence is circumstantial
   - **SPECULATIVE**: remove these — the mandate is evidence-based only
5. Group findings by severity, then by file

## Phase 5: REPORT

Present the evaluation report to the user.

## Phase 6: CLEANUP

After evaluation is complete:
1. Send `shutdown_request` to all evaluators via SendMessage
2. Wait for shutdown confirmations
3. Call TeamDelete to clean up the team

</team_workflow>

<output_format>
Present the evaluation in this format:

<evaluation_report>

### Evaluation Complete

**Verdict**: [PASS / PASS WITH ISSUES / NEEDS WORK / BLOCKED]
- BLOCKED: any CRITICAL issues remain
- NEEDS WORK: HIGH issues that should be fixed before merging
- PASS WITH ISSUES: MEDIUM/LOW issues noted but shippable
- PASS: clean across all evaluators

**Team Composition**: [N] evaluators
- **Correctness**: [N issues / Clean]
- **Architecture**: [N issues / Clean]
- **[Conditional evaluators]**: [summary]

**Spec Compliance** (if applicable):
- [X/Y] requirements fully implemented
- [list any PARTIAL or MISSING items]

### Findings by Severity

**CRITICAL** (must fix):
- [severity/domain] `file:line` — [description] — Evidence: [what proves this is an issue]

**HIGH** (should fix):
- [severity/domain] `file:line` — [description]

**MEDIUM** (fix or justify):
- [severity/domain] `file:line` — [description]

**LOW** (note):
- [severity/domain] `file:line` — [description]

### Cross-Cutting Patterns
- [Patterns that appeared across multiple evaluators, e.g., "silent error handling in 5 files"]

### What's Good
- [Explicitly call out things done well — balanced feedback prevents over-correction]

### Recommendation
[Next action — e.g., "Fix the 3 CRITICAL issues, then run `/devlyn.team-review` for a full review" or "Ship it"]

</evaluation_report>
</output_format>
</content>
</invoke>