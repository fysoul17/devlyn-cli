---
id: "J4"
title: "Apply decimal multiple arithmetic to referenced divisors"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Apply decimal multiple arithmetic to referenced divisors

## Context

Applications use `number.multiple(Joi.ref(...))` to validate an amount against a step supplied by another field or by validation context. Fractional steps should behave consistently with the same divisor supplied as a literal. Fix reference-based decimal validation while preserving Joi's existing arithmetic and reference semantics.

## Requirements

- [ ] `number.multiple()` accepts a reference resolving to a finite positive fractional divisor and makes the same validation decision as the equivalent literal divisor, for both sibling and context references.
- [ ] For a resolved divisor, both the decimal-place rejection and the scaled remainder calculation must use the divisor's precision, even when the value being validated has fewer decimal places.
- [ ] Each validation uses the current resolved divisor, including a sibling value converted by its number schema; reusing a schema with a different divisor must not retain arithmetic metadata from an earlier validation.
- [ ] Valid negative multiples and decimal numbers expressed in scientific notation follow the existing literal-divisor behavior when the divisor comes from a reference.
- [ ] A value with excess decimal precision or a nonzero scaled remainder fails with `number.multiple`; the error retains the original reference object in `details[0].context.multiple` and identifies the validated field's path.
- [ ] A reference resolving to a missing, nonnumeric, zero, negative, or nonfinite divisor continues to fail with `any.ref` under the existing argument validation rules.
- [ ] Literal divisors and integer reference divisors retain their existing behavior, and a schema reconstructed with `Joi.build(schema.describe())` retains decimal reference validation.
- [ ] Update the `number.multiple()` documentation in `API.md` to explain that numeric references use the same decimal arithmetic as literal divisors.

## Constraints

- **Limit changes to `lib/types/number.js`, `test/types/number.js`, and `API.md`.** This is a focused correction to the number rule and its tests and documentation.
- **Keep resolved arithmetic metadata local to each validation.** The stored rule arguments and reference must remain reusable for later validations and schema description.
- **Preserve the existing decimal-place calculation, precision rejection, and rounded scaled-remainder algorithm.** This change fixes how references participate in the established behavior without redefining numeric precision.
- **Add zero dependencies and preserve the public API and declarations.** Reference divisors already belong to the existing `number.multiple()` contract.
- **Keep the existing test, coverage, lint, and type-check settings.** The correction must meet the repository's normal quality checks.

## Out of Scope

- New validation methods, options, or reference syntax.
- General floating-point or arbitrary-precision arithmetic redesign.
- Changes to other numeric rules or to reference resolution and conversion order.
- Packaging, installation, or release changes.

<!-- devlyn:verification -->
## Verification

- `npm test` exits 0 from the repository root, offline with Node 22 and the installed devDependencies, including the existing 100% coverage threshold, lint, and type checks. The suite must cover fractional sibling and context references; a reused schema validating `0.75` with step `0.25`, `0.6` with step `0.2`, and `0.75` with a converted string step `'0.25'`; negative multiples and scientific notation; rejection of `0.65` and `0.251` with step `0.25`; original-reference error context; and rejection of a string context divisor. Existing literal-divisor and integer-reference checks must remain passing.

Source review must verify the full arithmetic contract, per-validation metadata lifetime, reference validation and error semantics, schema description and reconstruction, documentation, and change scope wherever these obligations are not established by the test suite.
