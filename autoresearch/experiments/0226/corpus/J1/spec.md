---
id: "J1"
title: "Honor UTF-8 byte budgets when truncating strings"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Honor UTF-8 byte budgets when truncating strings

## Context

Joi can measure a string's maximum length in encoded bytes, but truncation currently uses a UTF-16 code-unit offset regardless of that encoding. Applications enforcing UTF-8 storage or transport limits need truncation to return a prefix that fits the byte budget while preserving the retained text.

## Requirements

- [ ] With conversion enabled, `Joi.string().max(limit, encoding).truncate()` must retain the longest prefix of complete code points whose UTF-8 byte length does not exceed the resolved limit when the encoding is UTF-8.
- [ ] The UTF-8 spellings `utf8` and `utf-8` must be recognized case-insensitively and produce the same result.
- [ ] Truncation must preserve complete UTF-16 surrogate pairs and retain the original code units of each kept code point.
- [ ] A zero budget or a budget smaller than the first code point must yield an empty string; a string already within the budget must remain unchanged. Normal empty-string validation must still apply, including `string.empty` when empty strings are disallowed and success when they are allowed.
- [ ] A referenced maximum must use the resolved limit, including a converted sibling value. Missing or invalid referenced limits must retain the existing `any.ref` failure behavior.
- [ ] Truncation must operate on the result of the existing string transformations, preserving their order. For example, trimming ` xx ` and replacing `x` with `é` before truncating to three UTF-8 bytes must produce `é`.
- [ ] With conversion disabled or `.truncate(false)`, an over-limit value must retain the existing `string.max` failure behavior; disabling conversion must leave the input value unchanged.
- [ ] Truncation with no encoding or an encoding other than UTF-8 must retain its existing behavior, and enabling truncation without a maximum must remain a no-op.
- [ ] Validation must leave schema configuration unchanged so the same schema can be reused with different inputs and referenced limits.
- [ ] Document the UTF-8 byte-budget behavior in the existing `string.truncate()` entry in `API.md`.

## Constraints

- Limit changes to `lib/types/string.js`, `test/types/string.js`, and `API.md`, because this request changes existing string behavior without adding a public signature.
- Add zero dependencies, because the existing runtime facilities can measure UTF-8 byte lengths and retain string prefixes.
- Preserve the existing tests and the unmodified `npm test` command, including the 100% coverage threshold, lint, and type checks; do not add coverage-ignore directives, because the change must preserve the repository's regression guarantees.

## Out of Scope

- Preserving grapheme clusters or repairing surrogate code units that were already unpaired in the input.
- Changing truncation semantics for encodings other than UTF-8.
- Adding public methods, options, or TypeScript signatures.
- Refactoring unrelated string validation or conversion behavior.

<!-- devlyn:verification -->
## Verification

- `npm test`, run offline from the repository root with Node 22 and the installed devDependencies, must exit 0 with all tests passing, 100% coverage, and successful lint and type checks. The suite must cover exact and insufficient byte budgets with ASCII and BMP text, zero and oversized budgets, UTF-8 aliases, referenced limits and their errors, conversion preferences, and existing non-UTF-8 behavior. Include a compound case that trims and replaces text before applying the byte budget.
- Source review must confirm all requirements and constraints, including complete-code-point boundaries, preservation of retained code units, transformation order, reference handling, and schema reuse where the public suite does not exercise every combination.
