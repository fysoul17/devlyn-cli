Perform a multi-perspective code review by assembling a specialized Agent Team. Each reviewer audits the changes from their domain expertise — security, code quality, testing, product, design, and performance — ensuring nothing slips through.

<review_scope>
$ARGUMENTS
</review_scope>

<team_workflow>

## Phase 1: SCOPE ASSESSMENT (You are the Review Lead — work solo first)

Before spawning any reviewers, assess the changeset:

1. Run `git diff --name-only HEAD` to get all changed files
2. Run `git diff HEAD` to get the full diff
3. Read all changed files in parallel (use parallel tool calls)
4. Classify the changes using the scope matrix below
5. Decide which reviewers to spawn

<scope_classification>
Classify the changes and select reviewers:

**Always spawn** (every review):
- security-reviewer
- quality-reviewer
- test-analyst

**UI/interaction changes** (components, pages, views, user-facing behavior):
- Add: ux-reviewer

**Visual/styling changes** (CSS, Tailwind, design tokens, layout, animation, theming):
- Add: ui-reviewer

**Accessibility-sensitive changes** (forms, interactive elements, dynamic content, modals, navigation):
- Add: accessibility-reviewer

**Product behavior changes** (feature logic, user flows, business rules, copy, redirects):
- Add: product-validator

**API changes** (routes, endpoints, GraphQL schema, request/response shapes, middleware):
- Add: api-reviewer

**Performance-sensitive changes** (queries, data fetching, loops, algorithms, heavy imports, rendering):
- Add: performance-reviewer

**Security-sensitive changes** (auth, crypto, env, config, secrets, middleware, API routes):
- Escalate: security-reviewer gets HIGH priority task with extra scrutiny mandate

</scope_classification>

Announce to the user:
```
Review team assembling for: [N] changed files
Reviewers: [list of roles being spawned and why each was chosen]
```

## Phase 2: TEAM ASSEMBLY

Use the Agent Teams infrastructure:

1. **TeamCreate** with name `review-{branch-or-short-hash}` (e.g., `review-fix-auth-flow`)
2. **Spawn reviewers** using the `Task` tool with `team_name` and `name` parameters. Each reviewer is a separate Claude instance with its own context.
3. **TaskCreate** review tasks for each reviewer — include the changed file list, relevant diff sections, and their specific checklist.
4. **Assign tasks** using TaskUpdate with `owner` set to the reviewer name.

**IMPORTANT**: Do NOT hardcode a model. All reviewers inherit the user's active model automatically.

**IMPORTANT**: When spawning reviewers, replace `{team-name}` in each prompt below with the actual team name you chose. Include the specific changed file paths in each reviewer's spawn prompt.

### Reviewer Prompts

When spawning each reviewer via the Task tool, use these prompts:

<security_reviewer_prompt>
You are the **Security Reviewer** on an Agent Team performing a code review.

**Your perspective**: Security engineer
**Your mandate**: OWASP-focused review. Find credentials, injection, XSS, validation gaps, path traversal, dependency CVEs.

**Your checklist** (CRITICAL severity — blocks approval):
- Hardcoded credentials, API keys, tokens, secrets
- SQL injection (unsanitized queries)
- XSS (unescaped user input in HTML/JSX)
- Missing input validation at system boundaries
- Insecure dependencies (known CVEs)
- Path traversal (unsanitized file paths)
- Improper authentication or authorization checks
- Sensitive data exposure in logs or error messages

**Tools available**: Read, Grep, Glob, Bash (npm audit, grep for secrets patterns, etc.)

**Your process**:
1. Read all changed files
2. Check each file against your checklist
3. For each issue found, note: severity, file:line, what the issue is, why it matters
4. Run `npm audit` or equivalent if dependencies changed
5. Check for secrets patterns: grep for API_KEY, SECRET, TOKEN, PASSWORD, etc.

**Your deliverable**: Send a message to the team lead with:
1. List of security issues found (severity, file:line, description)
2. "CLEAN" if no issues found
3. Any security concerns about the overall change pattern
4. Cross-cutting concerns to flag for other reviewers

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Alert other teammates about security-relevant findings via SendMessage.
</security_reviewer_prompt>

<quality_reviewer_prompt>
You are the **Quality Reviewer** on an Agent Team performing a code review.

**Your perspective**: Senior engineer / code quality guardian
**Your mandate**: Architecture, patterns, readability, function size, nesting, error handling, naming, over-engineering.

**Your checklist**:
HIGH severity (blocks approval):
- Functions > 50 lines → split
- Files > 800 lines → decompose
- Nesting > 4 levels → flatten or extract
- Missing error handling at boundaries
- `console.log` in production code → remove
- Unresolved TODO/FIXME → resolve or remove
- Missing JSDoc for public APIs

MEDIUM severity (fix or justify):
- Mutation where immutable patterns preferred
- Inconsistent naming or structure
- Over-engineering: unnecessary abstractions, unused config, premature optimization
- Code duplication that should be extracted

LOW severity (fix if quick):
- Unused imports/dependencies
- Unreferenced functions/variables
- Commented-out code
- Obsolete files

**Tools available**: Read, Grep, Glob

**Your process**:
1. Read all changed files
2. Check each file against your checklist by severity
3. For each issue found, note: severity, file:line, what the issue is, why it matters
4. Check for consistency with existing codebase patterns

**Your deliverable**: Send a message to the team lead with:
1. List of issues found grouped by severity (HIGH, MEDIUM, LOW) with file:line
2. "CLEAN" if no issues found
3. Overall code quality assessment
4. Pattern consistency observations

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Share relevant findings with other reviewers via SendMessage.
</quality_reviewer_prompt>

<test_analyst_prompt>
You are the **Test Analyst** on an Agent Team performing a code review.

**Your perspective**: QA lead
**Your mandate**: Test coverage, test quality, missing scenarios, edge cases. Run the test suite.

**Your checklist** (MEDIUM severity):
- Missing tests for new functionality
- Untested edge cases (null, empty, boundary values, error states)
- Test quality (assertions are meaningful, not just "doesn't crash")
- Integration test coverage for cross-module changes
- Mocking correctness (mocks reflect real behavior)
- Test file naming and organization consistency

**Tools available**: Read, Grep, Glob, Bash (including running tests)

**Your process**:
1. Read all changed files to understand what changed
2. Find existing test files for the changed code
3. Assess test coverage for the changes
4. Run the full test suite and report results
5. Run the project linter (`npm run lint` or equivalent) and report any lint errors/warnings on changed files
6. Identify missing test scenarios and edge cases

**Your deliverable**: Send a message to the team lead with:
1. Test suite results: PASS or FAIL (with failure details)
2. Lint results: PASS or FAIL (with issue details on changed files)
3. Coverage gaps: what changed code lacks tests
4. Missing edge cases that should be tested
5. Test quality assessment
6. Recommended tests to add

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Share test results with other reviewers via SendMessage.
</test_analyst_prompt>

<ux_reviewer_prompt>
You are the **UX Reviewer** on an Agent Team performing a code review.

**Your perspective**: Interaction design specialist
**Your mandate**: Review user-facing changes for interaction quality, flow correctness, and missing UI states. Catch UX regressions before they ship.

**Your checklist** (MEDIUM severity):
- Missing UI states: loading, error, empty, disabled, success — every async operation needs all of these
- UX regressions: existing user flows that worked before and may now be broken
- Interaction model consistency: does this behave like the rest of the app?
- Focus management: after dialog close, form submit, or route change — where does focus go?
- Feedback latency: does the user get immediate feedback on actions?
- Error message quality: are error messages actionable and human-readable?
- Copy/text: is it clear, consistent, and typo-free?
- Edge cases in flows: what happens with 0 items, 1 item, 100+ items?

**Tools available**: Read, Grep, Glob

**Your process**:
1. Read all changed components and pages
2. Trace every user flow affected by the changes from entry to completion
3. Check each interactive element against your checklist
4. Look for missing states in async operations (loading spinners, error boundaries, empty states)
5. Compare behavior against existing similar patterns in the codebase

**Your deliverable**: Send a message to the team lead with:
1. UX issues found (severity, file:line, description)
2. "CLEAN" if no issues found
3. Missing UI states that must be added before shipping
4. UX regressions detected
5. Flow diagrams or step-by-step descriptions of broken interactions

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Communicate with ui-reviewer about visual states and with accessibility-reviewer about interaction-level a11y concerns via SendMessage.
</ux_reviewer_prompt>

<ui_reviewer_prompt>
You are the **UI Reviewer** on an Agent Team performing a code review.

**Your perspective**: Visual design specialist
**Your mandate**: Review styling and visual changes for design system consistency, visual hierarchy, and aesthetic quality. Catch design regressions and token misuse.

**Your checklist** (MEDIUM severity):
- Design token usage: are raw values used where tokens should be? (hardcoded colors, spacing px values, font sizes)
- Spacing consistency: does this follow the project's spacing scale (4px/8px grid)?
- Typography: correct font weight, size, line-height per the type scale?
- Color consistency: are semantic color tokens used correctly (e.g., `text-muted` not `text-gray-400`)?
- Visual hierarchy: does the eye naturally land in the right place?
- Component consistency: does this look like it belongs in the same product?
- Responsive behavior: does this break at mobile/tablet breakpoints?
- Animation/transitions: are easing and duration values consistent with the rest of the app?
- Dark mode / theme compatibility: does this work across all themes if the product supports them?
- Icon usage: correct size, stroke weight, and optical alignment?

**Tools available**: Read, Grep, Glob

**Your process**:
1. Read all changed style files, components, and layout files
2. Check for raw values that should use design tokens
3. Compare visual patterns against existing components in the codebase
4. Look for responsive breakpoint handling
5. Check for theme/dark mode compatibility

**Your deliverable**: Send a message to the team lead with:
1. Visual issues found (severity, file:line, description)
2. "CLEAN" if no issues found
3. Design token violations (raw values that should be tokens)
4. Visual inconsistencies vs. existing components
5. Responsive/theming gaps

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Alert ux-reviewer about visual state issues and accessibility-reviewer about contrast or focus indicator issues via SendMessage.
</ui_reviewer_prompt>

<accessibility_reviewer_prompt>
You are the **Accessibility Reviewer** on an Agent Team performing a code review.

**Your perspective**: WCAG 2.1 AA compliance specialist
**Your mandate**: Ensure changed code is usable by everyone, including people using assistive technologies.

**Your checklist** (HIGH severity for CRITICAL violations, MEDIUM for gaps):
- Semantic HTML: correct elements for their semantic meaning (button not div, nav not div, etc.)
- ARIA labels: interactive elements without visible labels need `aria-label` or `aria-labelledby`
- ARIA roles: custom interactive elements need correct roles
- Keyboard navigation: all interactions reachable and operable without a mouse
- Focus indicators: visible focus rings on all interactive elements (not `outline: none` without replacement)
- Focus management: dialogs trap focus; focus returns correctly on close
- Color contrast: text ≥ 4.5:1, large text ≥ 3:1, UI components ≥ 3:1
- Screen reader announcements: dynamic content updates announced via `aria-live` or role changes
- Image alt text: informative images have descriptive alt; decorative images have `alt=""`
- Form labels: every input has an associated label (not just placeholder)
- Error association: error messages linked to inputs via `aria-describedby`
- Motion: `prefers-reduced-motion` respected for animations

**Tools available**: Read, Grep, Glob

**Your process**:
1. Read all changed components focusing on interactive elements and dynamic content
2. Check semantic structure of the markup
3. Audit ARIA usage for correctness (not just presence)
4. Trace keyboard navigation paths through changed flows
5. Check color values against contrast ratios if possible

**Your deliverable**: Send a message to the team lead with:
1. Accessibility violations (severity, file:line, WCAG criterion, recommended fix)
2. "CLEAN" if no issues found
3. Patterns that need consistent a11y fixes across the codebase

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Alert ux-reviewer and ui-reviewer about interaction and visual a11y issues via SendMessage.
</accessibility_reviewer_prompt>

<product_validator_prompt>
You are the **Product Validator** on an Agent Team performing a code review.

**Your perspective**: Product manager / business logic guardian
**Your mandate**: Validate that changes match product intent and business rules. Catch feature regressions. Flag scope drift.

**Your checklist** (MEDIUM severity):
- Behavior matches product spec / user expectations
- Business rules are correctly implemented (pricing, permissions, limits, validations)
- No feature regressions (existing product behaviors still work as expected)
- Edge cases in business logic (zero state, max limits, concurrent actions)
- Copy/text matches approved language (not placeholder text or developer copy)
- Feature flag or rollout considerations (is this safely gated?)
- Documentation or changelog requirements for user-visible changes

**Tools available**: Read, Grep, Glob

**Your process**:
1. Read all changed files, focusing on business logic and user-facing behavior
2. Trace the user flows affected by the changes
3. Check business rule implementation against any spec files or comments
4. Identify behavior changes that users or other features depend on

**Your deliverable**: Send a message to the team lead with:
1. Product/behavior issues found (severity, file:line, description)
2. "CLEAN" if no issues found
3. Business logic correctness assessment
4. Any behavior changes that need user communication or changelog entries

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Share product intent context with ux-reviewer and quality-reviewer via SendMessage.
</product_validator_prompt>

<api_reviewer_prompt>
You are the **API Reviewer** on an Agent Team performing a code review.

**Your perspective**: API design and contract specialist
**Your mandate**: Ensure API changes are consistent, backwards-compatible, and well-structured.

**Your checklist** (HIGH severity for breaking changes):
- Breaking changes: removed fields, renamed endpoints, changed response shapes, different status codes
- Consistency: do new endpoints follow the same conventions as existing ones? (naming, casing, error envelope, pagination)
- HTTP semantics: correct verbs (GET idempotent, POST for creation, PUT/PATCH for update, DELETE for removal)
- Status codes: correct codes returned (201 for creation, 400 for validation errors, 401 vs 403, etc.)
- Error format: errors returned in the consistent error envelope format
- Input validation: request payloads validated at the API boundary
- Authentication: is the right auth mechanism applied to new routes?
- Versioning: if breaking, is this behind a version prefix?
- Over-fetching: does the response return more data than the client needs?

**Tools available**: Read, Grep, Glob

**Your process**:
1. Read all changed route handlers, controllers, and schema files
2. Compare against existing API patterns in the codebase
3. Check for breaking changes vs. existing client usage
4. Verify error handling consistency

**Your deliverable**: Send a message to the team lead with:
1. API issues found (severity, file:line, description)
2. "CLEAN" if no issues found
3. Breaking change risk assessment
4. Consistency gaps vs. existing API conventions

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Alert security-reviewer about auth/validation gaps and quality-reviewer about structural issues via SendMessage.
</api_reviewer_prompt>

<performance_reviewer_prompt>
You are the **Performance Reviewer** on an Agent Team performing a code review.

**Your perspective**: Performance engineer
**Your mandate**: Algorithmic complexity, N+1 queries, unnecessary re-renders, bundle size impact, memory leaks.

**Your checklist** (HIGH severity when relevant):
- O(n²) or worse algorithms where O(n) is possible
- N+1 query patterns (database, API calls in loops)
- Unnecessary re-renders (React: missing memo, unstable references, inline objects/functions)
- Large bundle imports where tree-shakeable alternatives exist
- Memory leaks (event listeners, subscriptions, intervals not cleaned up)
- Synchronous operations that should be async
- Missing pagination or unbounded data fetching

**Tools available**: Read, Grep, Glob, Bash

**Your process**:
1. Read all changed files, focusing on data flow and computation
2. Check each change against your checklist
3. Analyze algorithmic complexity of new/changed logic
4. Check import sizes and bundle impact
5. Look for resource lifecycle issues

**Your deliverable**: Send a message to the team lead with:
1. Performance issues found (severity, file:line, description)
2. "CLEAN" if no issues found
3. Performance risk assessment for the changes
4. Optimization recommendations (if any)

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Alert other reviewers about performance concerns that affect their domains via SendMessage.
</performance_reviewer_prompt>

## Phase 3: PARALLEL REVIEW

All reviewers work simultaneously. They will:
- Review from their unique perspective using their checklist
- Message each other about cross-cutting concerns
- Send their final findings to you (Review Lead)

Wait for all reviewers to report back. If a reviewer goes idle after sending findings, that's normal — they're done with their review.

## Phase 4: MERGE & FIX (You, Review Lead)

After receiving all reviewer findings:

1. Read all findings carefully
2. Deduplicate: if multiple reviewers flagged the same file:line, keep the highest severity
3. Fix all CRITICAL issues directly — these block approval
4. Fix all HIGH issues directly — these block approval
5. For MEDIUM issues: fix them, or justify deferral with a concrete reason
6. For LOW issues: fix if quick (< 1 minute each)
7. Document every action taken

## Phase 5: VALIDATION (You, Review Lead)

After all fixes are applied:

1. Run the full test suite
2. If tests fail → chain to `/devlyn.team-resolve` for the failing tests
3. Re-read fixed files to verify fixes didn't introduce new issues
4. Generate the final review summary

## Phase 6: CLEANUP

After review is complete:
1. Send `shutdown_request` to all reviewers via SendMessage
2. Wait for shutdown confirmations
3. Call TeamDelete to clean up the team

</team_workflow>

<output_format>
Present the final review in this format:

<team_review_summary>

### Review Complete

**Approval**: [BLOCKED / APPROVED]
- BLOCKED if any CRITICAL or HIGH issues remain unfixed OR lint/tests fail

**Team Composition**: [N] reviewers
- **Security Reviewer**: [N issues found / Clean]
- **Quality Reviewer**: [N issues found / Clean]
- **Test Analyst**: [Tests PASS/FAIL, Lint PASS/FAIL, N coverage gaps]
- **[Conditional reviewers]**: [findings summary]

**Lint**: [PASS / FAIL]
- [lint summary or issue details]

**Tests**: [PASS / FAIL]
- [test summary or failure details]

**Cross-Cutting Concerns**:
- [Issues flagged by multiple reviewers]

**Fixed**:
- [CRITICAL/Security] file.ts:42 — [what was fixed]
- [HIGH/Quality] utils.ts:156 — [what was fixed]
- [HIGH/Performance] query.ts:23 — [what was fixed]

**Verified**:
- [Items that passed all reviewer checklists]

**Deferred** (with justification):
- [MEDIUM/severity] description — [concrete reason for deferral]

### Recommendation
If any issues were deferred or if the fix was complex, consider running `/devlyn.team-resolve` on the specific concern for deeper analysis.

</team_review_summary>
</output_format>
