---
id: "J2"
title: "Allow plugins to move an existing rule before another rule"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Allow plugins to move an existing rule before another rule

## Context

Plugins can insert and replace rules, but cannot change the position of an existing rule without reconstructing its registration. That reconstruction can lose its enabled state or membership in alternate chains. A small rule-moving API would let plugins adjust precedence while retaining that registration.

## Requirements

- [ ] Add `Ruler.moveBefore(ruleName: string, beforeName: string): void`, available on the existing core, block, and inline rulers, to relocate an existing rule immediately before the named anchor.
- [ ] The resulting order must place the moved rule immediately before the anchor whether its original position was earlier or later than the anchor; all other rules must retain their relative order.
- [ ] Moving a rule must retain its name, function identity, enabled state, and alternate-chain membership; every chain must reflect the resulting registration order when next obtained through `getRules`.
- [ ] Moving a rule before itself or before its already immediate successor must leave the registration order unchanged.
- [ ] Resolve names by the existing first-match convention. If either name is absent, throw `Error` with `Parser rule not found: NAME` for the first absent name in argument order, and leave registration order and enabled states unchanged.
- [ ] Previously compiled rule chains must not prevent a successful move from taking effect on subsequent `getRules` calls or parsing; arrays returned before the move need not be updated in place.

## Constraints

- **Limit changes to `src/ruler.ts` and `test/markdown-it/ruler.test.mjs`.** Moving an existing registration belongs in the rule manager, with coverage in its existing suite.
- **Do not recreate a moved rule using insertion defaults or change existing rule-management APIs.** Plugins rely on disabled registrations and alternate chains surviving a move.
- **Document the new method alongside the existing methods.** The rule manager is part of the plugin API.
- **Add no dependencies and do not change `package.json` or `package-lock.json`.** The existing array operations and test tools are sufficient.

## Out of Scope

- Moving rules between rulers, adding `moveAfter`, or accepting numeric positions.
- Renaming rules, changing duplicate-name policy, or changing chain-array ownership.
- Automatic ordering based on declared plugin dependencies.

<!-- devlyn:verification -->
## Verification

- `PATH=/Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/markdown-it/node-bin:$PATH npm test` exits 0. It runs the configured lint, build, type checks, CommonMark tests, library tests, and build tests. Added tests move a later rule before an earlier anchor after warming both default and alternate chains, preserve a disabled rule through a move and re-enable, and cover no-op and missing-name cases.

Ordering combinations and registration-preservation semantics beyond those exercised by the suite remain source-review obligations. No additional standalone lint or type command is needed because `npm test` runs both and propagates their failures.
