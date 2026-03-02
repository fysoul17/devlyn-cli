# Code Review Standards

Severity framework and quality bar for reviewing code changes. Apply this framework whenever reviewing, auditing, or validating code.

## Trigger

- Post-implementation review
- Code review requests
- PR review or diff analysis
- Any use of `/devlyn.review` or `/devlyn.team-review`

## Severity Framework

### CRITICAL — Security (blocks approval)

- Hardcoded credentials, API keys, tokens, secrets
- SQL injection (unsanitized queries)
- XSS (unescaped user input in HTML/JSX)
- Missing input validation at system boundaries
- Insecure dependencies (known CVEs)
- Path traversal (unsanitized file paths)

### HIGH — Code Quality (blocks approval)

- Functions > 50 lines → split
- Files > 800 lines → decompose
- Nesting > 4 levels → flatten or extract
- Missing error handling at boundaries
- `console.log` in production code → remove
- Unresolved TODO/FIXME → resolve or remove

### MEDIUM — Best Practices (fix or justify)

- Mutation where immutable patterns preferred
- Missing tests for new functionality
- Accessibility gaps (alt text, ARIA, keyboard nav)
- Inconsistent naming or structure
- Over-engineering: unnecessary abstractions, premature optimization

### LOW — Cleanup (fix if quick)

- Unused imports/dependencies
- Unreferenced functions/variables
- Commented-out code
- Obsolete files

## Approval Criteria

**BLOCKED** if any of:
- CRITICAL issues remain unfixed
- HIGH issues remain unfixed
- Lint fails
- Tests fail

**APPROVED** when:
- All CRITICAL and HIGH issues are fixed
- MEDIUM issues are fixed or have concrete justification for deferral
- Lint passes
- Test suite passes

## Routing

- **Quick review** (few files, straightforward changes): Use `/devlyn.review`
- **Thorough review** (many files, security-sensitive, user-facing): Use `/devlyn.team-review` for multi-perspective coverage
