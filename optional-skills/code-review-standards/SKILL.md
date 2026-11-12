---
name: code-review-standards
description: Severity framework (CRITICAL security, HIGH correctness and data, MEDIUM best practice, LOW cleanup) and approval criteria for judging a code change. Use when reviewing, auditing or validating a diff, pull request or just-finished implementation, or when deciding whether a change is ready to approve.
---
# Code Review Standards

Severity framework and quality bar for reviewing code changes. Apply this framework whenever reviewing, auditing, or validating code.

## Severity Framework

A CRITICAL or HIGH finding names its concrete case: the input, state or path that leads to the harm. A finding that cannot name one is MEDIUM or lower.

### CRITICAL — Security (blocks approval)

- Hardcoded credentials, API keys, tokens, secrets
- SQL injection (unsanitized queries)
- XSS (unescaped user input in HTML/JSX)
- Missing input validation at system boundaries
- Insecure dependencies (known CVEs)
- Path traversal (unsanitized file paths)

### HIGH — Correctness and data (blocks approval)

- Wrong behavior or results
- Lost or corrupted data
- Missing error handling at a boundary, where a failure there gives one of the above

### MEDIUM — Best Practices (fix or justify)

- Functions > 50 lines → split
- Files > 800 lines → decompose
- Nesting > 4 levels → flatten or extract
- `console.log` in production code → remove
- Unresolved TODO/FIXME → resolve or remove
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
