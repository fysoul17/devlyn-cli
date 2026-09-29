---
id: "J2"
title: "Trim whitespace as a fallback for custom boolean values"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Trim whitespace as a fallback for custom boolean values

## Context

Joi already accepts whitespace around the built-in boolean strings `true` and `false`, but custom strings registered with `boolean.truthy()` and `boolean.falsy()` do not receive the same treatment. Configuration values such as `' yes '` should be usable without preprocessing. Add whitespace fallback while preserving deliberately padded registrations and the existing conversion preferences.

## Requirements

- [ ] With conversion enabled, a string that does not resolve through the built-in boolean conversion must be eligible for custom truthy/falsy matching both as supplied and with leading and trailing whitespace removed by JavaScript string trimming. A truthy match returns `true`; a falsy match returns `false`.
- [ ] For custom mappings, a match against the original input must take precedence over a match found only after trimming; truthy must take precedence over falsy for the same candidate.
- [ ] Actual booleans must remain unchanged. Built-in recognition of the trimmed strings `true` and `false` must retain precedence over custom mappings and continue to honor `boolean.sensitive()`.
- [ ] Both original-input and trimmed-input custom matching must use the existing sensitivity setting: case insensitive by default, case sensitive when enabled. Disabling conversion must disable the whitespace fallback along with other boolean coercion.
- [ ] Registered truthy and falsy values must remain unchanged. A padded registration must still match its original spelling, and registering a padded string alone must not make its unpadded spelling valid.
- [ ] Custom matching of non-string values must retain its current behavior without string conversion or trimming.
- [ ] If neither built-in nor custom conversion matches, validation must retain the original input, including whitespace, in the returned value and `boolean.base` error context.
- [ ] Document the whitespace fallback, matching precedence, and unchanged sensitivity behavior in the `boolean.truthy()` and `boolean.falsy()` sections of `API.md`.

## Constraints

- Limit changes to `lib/types/boolean.js`, `test/types/boolean.js`, and `API.md`, because this extends existing boolean coercion without changing the public API or type declarations.
- Add no dependencies, because existing string operations and Joi value matching support this behavior.
- Retain existing tests and the unchanged `npm test` coverage, lint, and type checks, because existing boolean behavior must remain compatible.

## Out of Scope

- New boolean methods, options, or TypeScript declarations.
- Whitespace normalization of registered values or non-boolean schema types.
- Changes to boolean casting, schema descriptions, or error messages.

<!-- devlyn:verification -->
## Verification

- `node --version` reports Node 22.
- Run `npm test` from the repository root with the installed development dependencies; it must exit 0 with the existing 100% coverage threshold, lint, and type checks intact. The suite must cover padded custom truthy/falsy values, unpadded values, unmatched input preservation, sensitivity and disabled conversion, canonical strings competing with custom mappings, actual booleans, numeric mappings, truthy/falsy overlap for the same candidate, and padded registrations that remain distinct from unpadded spellings.

Source review must confirm matching precedence, preservation of registered values and unmatched error context, documentation accuracy, and the stated change scope alongside the suite results.
