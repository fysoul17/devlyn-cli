Perform a comprehensive post-implementation review. After receiving tool results, carefully reflect on their quality and determine optimal next steps before proceeding.

<escalation>
If the changeset is large (10+ files), touches multiple domains (UI + API + auth), or requires multi-perspective judgment, escalate to `/devlyn.team-review` instead of solo review.
</escalation>

<procedure>
1. Run `git diff --name-only HEAD` to get all changed files
2. Read all changed files in parallel (use parallel tool calls)
3. Check each file against the review checklist below
4. Fix issues directly — do not just suggest fixes
5. Run linter (`npm run lint` or equivalent) and fix all reported lint issues
6. Run test suite to verify changes don't break existing functionality
7. If lint or tests fail → use `/devlyn.resolve` workflow to fix, then re-run
8. Generate summary report with file:line references
9. Block approval if any CRITICAL or HIGH issues remain unfixed OR tests fail
</procedure>

<investigate_before_fixing>
ALWAYS read files before proposing edits. Do not speculate about code you have not inspected. Verify assumptions by reading actual implementation. Give grounded, hallucination-free assessments.
</investigate_before_fixing>

<use_parallel_tool_calls>
Make all independent tool calls in parallel. When reviewing 5 files, run 5 read calls simultaneously. Only execute sequentially when edits depend on prior reads. Never guess parameters.
</use_parallel_tool_calls>

<review_checklist>

## CRITICAL — Security (must fix, blocks approval)

- Hardcoded credentials, API keys, tokens, secrets
- SQL injection (unsanitized queries)
- XSS (unescaped user input in HTML/JSX)
- Missing input validation at system boundaries
- Insecure dependencies (known CVEs)
- Path traversal (unsanitized file paths)

## HIGH — Code Quality (must fix, blocks approval)

- Functions > 50 lines → split
- Files > 800 lines → decompose
- Nesting > 4 levels → flatten or extract
- Missing error handling at boundaries
- `console.log` in production code → remove
- Unresolved TODO/FIXME → resolve or remove
- Missing JSDoc for public APIs

## MEDIUM — Best Practices (fix or justify)

**Logic & structure**:
- Mutation where immutable patterns preferred
- Missing tests for new functionality
- Inconsistent naming or structure
- Over-engineering: unnecessary abstractions, unused config, premature optimization

**UI & interaction** (apply when components or pages changed):
- Missing UI states: every async operation must handle loading, error, empty, and disabled — flag any that are absent
- UX regressions: existing user flows that may now be broken
- Copy/text: placeholder text, inconsistent wording, or developer-written strings left in

**Visual & design** (apply when styles, layout, or tokens changed):
- Raw values where design tokens should be used (hardcoded colors, px spacing, font sizes)
- Visual inconsistency vs. existing components
- Responsive/breakpoint gaps

**Accessibility** (apply when any UI changed):
- Missing semantic HTML (div used as button, etc.)
- Interactive elements without accessible labels (aria-label, aria-labelledby)
- Missing keyboard navigation support
- Insufficient color contrast
- Missing focus indicators (outline: none without replacement)
- Dynamic content not announced to screen readers (aria-live)
- Form inputs without associated labels

**Performance** (apply when data fetching, loops, or rendering changed):
- N+1 query or API call patterns (calls inside loops)
- Unnecessary re-renders (React: missing memo, unstable references, inline objects/functions)
- Unbounded data fetching without pagination
- Memory leaks (event listeners, subscriptions, timers not cleaned up)

**API** (apply when routes, endpoints, or schema changed):
- Breaking changes: removed fields, renamed endpoints, changed response shapes
- HTTP verb or status code misuse
- Missing input validation at the API boundary
- Inconsistency with existing API conventions (naming, error envelope, auth)

## LOW — Cleanup (fix if quick)

- Unused imports/dependencies
- Unreferenced functions/variables
- Commented-out code
- Obsolete files

</review_checklist>

<action_instructions>
For each issue:

1. State severity, file:line
2. One sentence: what and why it matters
3. Make the fix immediately
4. Continue to next issue

Be persistent. Complete the full review before stopping.
</action_instructions>

<output_format>
<review_summary>

### Review Complete

**Approval**: [BLOCKED / APPROVED]

- BLOCKED if any CRITICAL or HIGH issues remain unfixed OR lint/tests fail

**Lint**: [PASS / FAIL]
- [lint summary or issue details]

**Tests**: [PASS / FAIL]
- [test summary or failure details]

**Fixed**:
- [CRITICAL] file.ts:42 — Removed hardcoded API key
- [HIGH] utils.ts:156 — Split 80-line function
- [MEDIUM/UI] Button.tsx:23 — Added loading and error states
- [MEDIUM/A11y] Input.tsx:11 — Added aria-label to unlabeled input

**Verified**:
- Authentication flow handles edge cases
- Input validation at API boundaries

**Deferred** (with justification):
- [MEDIUM] Missing tests — existing coverage adequate for hotfix

</review_summary>
</output_format>
