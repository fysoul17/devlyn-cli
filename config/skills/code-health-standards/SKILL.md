# Code Health Standards

Standards for keeping codebases lean and maintainable. Apply these thresholds during development — catching debt early is cheaper than cleaning it later.

## Trigger

- Writing new code or modifying existing code
- Adding dependencies
- Creating new files or modules
- Refactoring or restructuring code
- Any use of `/devlyn.clean`, `/devlyn.resolve`, or `/devlyn.review`

## Dead Code Prevention

When writing code, check that you aren't creating orphans:

- **Before deleting a function**: Verify its callers are also updated or removed
- **Before renaming an export**: Search for all import sites
- **After removing a feature**: Trace and remove all supporting code (types, utils, tests, styles)
- **After removing a dependency**: Remove all import statements referencing it

When reviewing code, flag anything with zero inbound references that isn't an entry point.

## Dependency Discipline

Before adding a new dependency, check:

1. Can this be done with language built-ins or existing deps?
2. Is there already a dependency that covers this use case?
3. What is the bundle size impact?
4. Is the package actively maintained?

Prefer the standard library over external packages for simple operations (string manipulation, array utilities, date formatting in modern JS/TS).

## Complexity Thresholds

Keep code within these bounds:

| Metric | Threshold | Action |
|--------|-----------|--------|
| Function length | > 50 lines | Split into focused sub-functions |
| File length | > 500 lines | Decompose into modules |
| Nesting depth | > 4 levels | Flatten with early returns or extraction |
| Parameters | > 5 per function | Use an options object |
| Cyclomatic complexity | > 10 per function | Simplify branching logic |

These aren't arbitrary — they correlate with defect density in research. Treat them as guardrails, not rules.

## Naming Consistency

Follow the project's established conventions. If none exist:

- **Files**: Match the framework convention (PascalCase for React components, kebab-case for utilities, etc.)
- **Variables/functions**: camelCase (JS/TS), snake_case (Python/Rust), follow language idiom
- **Constants**: UPPER_SNAKE_CASE for true constants, camelCase for computed values
- **Types/interfaces**: PascalCase

When you notice inconsistent naming in code you're touching, align it with the dominant pattern — but only for code in your changeset.

## Production Code Hygiene

Code committed to production should not contain:

- `console.log` / `print` statements (use the project's logger)
- Commented-out code blocks (use version control, not comments)
- TODO/FIXME without a linked issue or timeline
- Empty catch blocks or swallowed errors
- Hardcoded secrets, API keys, or environment-specific URLs
- Type `any` (TypeScript) without a justifying comment

## Routing

- **Active cleanup**: Use `/devlyn.clean` to scan and remove accumulated debt
- **Focused cleanup**: Use `/devlyn.clean [category]` for targeted sweeps (dead code, deps, tests, complexity, hygiene)
