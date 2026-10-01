---
id: "J3"
title: "Preserve parser configuration when a rule batch contains unknown names"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Preserve parser configuration when a rule batch contains unknown names

## Context

`MarkdownIt.enable` and `MarkdownIt.disable` accept a batch of names spanning several rule managers. Today a batch can change known rules and then throw for an unknown name, leaving a parser partially reconfigured. Applications that catch a configuration error should be able to keep using the parser with its previous behavior.

## Requirements

- [ ] With `ignoreInvalid` omitted or false, determine whether every requested name exists before committing a batch; if any name is unknown, throw the existing operation-specific error and apply none of the requested enabled-state changes.
- [ ] After a rejected batch, enabled states and the function sequences returned by default and alternate chains must be equivalent to their pre-call values across `core.ruler`, `block.ruler`, `inline.ruler`, and `inline.ruler2`, including when chains were already compiled.
- [ ] On success, enable or disable each requested name in every one of those four rulers where it is found, using each ruler's existing first-match behavior, and return the same `MarkdownIt` instance; a name shared by the primary and secondary inline rulers must affect both.
- [ ] With `true` supplied as the second argument (`ignoreInvalid`), ignore unknown names and apply all known names, including batches containing only unknown names.
- [ ] Preserve string input, empty arrays, repeated names, and the input array itself. For strict failures, retain the error text `MarkdownIt. Failed to enable unknown rule(s): NAMES` or `MarkdownIt. Failed to disable unknown rule(s): NAMES`, where `NAMES` is the comma-joined sequence of unknown input names in input order, including repetitions.
- [ ] Rendering after a rejected batch must behave as it did before that call, and a later valid batch on the same instance must still take effect.

## Constraints

- **Limit changes to `src/markdownit.ts` and `test/markdown-it/misc.test.mjs`.** This request concerns the top-level batch API, whose name lookup spans multiple rulers.
- **Keep public signatures and successful rule ordering unchanged.** Existing plugins and method chaining must remain compatible.
- **Add no dependencies and do not change `package.json` or `package-lock.json`.** Validation can use the existing rule-manager data and test tools.

## Out of Scope

- Atomicity of direct calls to `Ruler.enable`, `Ruler.disable`, `Ruler.enableOnly`, or `MarkdownIt.configure`.
- Recovery from user-replaced rule-manager methods that throw, or from arbitrary plugin callbacks.
- Renaming rules, rejecting duplicate registrations, or changing presets.

<!-- devlyn:verification -->
## Verification

- `PATH=/Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/markdown-it/node-bin:$PATH npm test` exits 0. It runs the configured lint, build, type checks, CommonMark tests, library tests, and build tests. Added tests warm rule chains, reject mixed batches of known and unknown names, compare state and rendering, and then apply a valid batch on the same instance. Tests also cover successful shared-name changes, permissive calls, and error formatting.

Failure-state preservation across ruler combinations and previously compiled chains beyond those exercised by the suite remains a source-review obligation. No additional standalone lint or type command is needed because `npm test` runs both and propagates their failures.
