---
id: "J4"
title: "Include parsed destination and title in reference definition metadata"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Include parsed destination and title in reference definition metadata

## Context

Plugins can retain hidden `reference_definition` tokens by disabling the `strip_references` core rule. Those tokens currently identify the label and source lines, but a plugin must consult the document-wide reference lookup for the destination and title. Source inspection tools need the parsed values belonging to the definition at each token's source location.

## Requirements

- [ ] Every emitted `reference_definition` token must have a null-prototype `meta` object with its existing normalized `label` plus string fields `href` and `title`.
- [ ] `meta.href` must be the normalized, validated destination parsed from that definition, and `meta.title` must be its decoded parsed title, or the empty string when that definition has no accepted title.
- [ ] The metadata and `map` of a definition token must describe the same source occurrence, including when another definition with the same normalized label, or a pre-populated `env.references` entry, determines link resolution.
- [ ] Preserve first-definition-wins lookup behavior in `env.references`, its existing `{ href, title }` entry shape, and the destinations and titles used by links and images.
- [ ] Preserve the parser's existing multiline-title and fallback behavior: a rejected title continuation must not appear in metadata or extend the definition's source map past the accepted definition.
- [ ] Keep definition tokens hidden and stripped by default; retaining them must leave rendered HTML unchanged. Inline link and image metadata must retain their existing label-only shape.

## Constraints

- **Limit changes to `src/rules_block/reference.ts` and `test/markdown-it/misc.test.mjs`.** The occurrence-specific parsed values already exist where definition tokens are emitted.
- **Store the metadata as a separate snapshot rather than aliasing an `env.references` entry.** Plugins may edit token metadata without changing how other tokens resolve references.
- **Add no dependencies and do not change `package.json` or `package-lock.json`.** Existing parsing and test helpers provide everything needed.

## Out of Scope

- Raw source spelling, character offsets, duplicate-definition diagnostics, or new token types.
- Changing reference-label normalization, URL validation, title syntax, or reference precedence.
- Exposing definition tokens by default or adding a renderer for them.

<!-- devlyn:verification -->
## Verification

- `PATH=/Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/markdown-it/node-bin:$PATH npm test` exits 0. It runs the configured lint, build, type checks, CommonMark tests, library tests, and build tests. Added tests retain definitions, check their metadata and source maps, exercise multiline and rejected-title continuations, and verify snapshot independence and unchanged rendering.

Semantics beyond those exercised by the suite remain source-review obligations. No additional standalone lint or type command is needed because `npm test` runs both and propagates their failures.
