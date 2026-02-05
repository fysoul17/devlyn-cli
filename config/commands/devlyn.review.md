Perform a comprehensive post-implementation review. After receiving tool results, carefully reflect on their quality and determine optimal next steps before proceeding.

<procedure>
1. Run `git diff --name-only HEAD` to get all changed files
2. Read all changed files in parallel (use parallel tool calls)
3. Check each file against the review checklist below
4. Fix issues directly—do not just suggest fixes
5. Run test suite to verify changes don't break existing functionality
6. If tests fail → use devlyn.resolve workflow to fix, then re-run tests
7. Generate summary report with file:line references
8. Block approval if any CRITICAL or HIGH issues remain unfixed OR tests fail
</procedure>

<investigate_before_fixing>
ALWAYS read files before proposing edits. Do not speculate about code you have not inspected. Verify assumptions by reading actual implementation. Give grounded, hallucination-free assessments.
</investigate_before_fixing>

<use_parallel_tool_calls>
Make all independent tool calls in parallel. When reviewing 5 files, run 5 read calls simultaneously. Only execute sequentially when edits depend on prior reads. Never guess parameters.
</use_parallel_tool_calls>

<review_checklist>

## CRITICAL — Security (must fix, blocks approval)

Security vulnerabilities can cause data breaches and system compromise:

- Hardcoded credentials, API keys, tokens, secrets
- SQL injection (unsanitized queries)
- XSS (unescaped user input in HTML/JSX)
- Missing input validation at system boundaries
- Insecure dependencies (known CVEs)
- Path traversal (unsanitized file paths)

## HIGH — Code Quality (must fix, blocks approval)

These issues cause bugs or significant maintenance burden:

- Functions > 50 lines → split
- Files > 800 lines → decompose
- Nesting > 4 levels → flatten or extract
- Missing error handling at boundaries
- `console.log` in production code → remove
- Unresolved TODO/FIXME → resolve or remove
- Missing JSDoc for public APIs

## MEDIUM — Best Practices (fix or justify)

- Mutation where immutable patterns preferred
- Missing tests for new functionality
- Accessibility gaps (alt text, ARIA, keyboard nav)
- Inconsistent naming or structure
- Over-engineering: unnecessary abstractions, unused config, premature optimization

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

- BLOCKED if any CRITICAL or HIGH issues remain unfixed OR tests fail

**Tests**: [PASS / FAIL]
- [test summary or failure details]

**Fixed**:
- [CRITICAL] file.ts:42 — Removed hardcoded API key
- [HIGH] utils.ts:156 — Split 80-line function

**Verified**:
- Authentication flow handles edge cases
- Input validation at API boundaries

**Deferred** (with justification):
- [MEDIUM] Missing tests — existing coverage adequate for hotfix

</review_summary>
</output_format>
