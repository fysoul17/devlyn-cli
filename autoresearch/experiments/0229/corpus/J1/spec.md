---
id: "J1"
title: "Scope inline lookahead caching to the active source range"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Scope inline lookahead caching to the active source range

## Context

Inline plugins can temporarily narrow `StateInline.posMax` when examining a portion of a paragraph, then restore the larger range. `ParserInline.skipToken` memoizes where a token ends, but currently associates that answer only with its starting position. Reusing an answer from another range can make a later lookahead skip the wrong text.

## Requirements

- [ ] For a fixed source, rule configuration, environment, and nesting context, `skipToken(state)` must produce the same ending `state.pos` as an uncached call at the same starting position and current `state.posMax`.
- [ ] A cached answer may be reused only when it was computed with the current `state.posMax`; changing the upper bound in either direction must cause that position to be examined again, even when its cached ending position lies within the new range.
- [ ] Repeated lookahead at the same position with the same upper bound must continue to use the cached answer without invoking the inline rules again.
- [ ] Lookahead must retain its existing silent behavior: it must not emit tokens or append pending text, and must restore the nesting level after invoking a successful inline rule.
- [ ] Ordinary full-paragraph parsing, Markdown rendering, and the existing protection against pathological input must remain compatible with the pinned implementation.

## Constraints

- **Limit changes to `src/parser_inline.ts`, `src/rules_inline/state_inline.ts`, and `test/markdown-it/inline-cache.test.mjs`.** This keeps the fix within lookahead state and its regression coverage.
- **Keep `state.cache` as a numeric start-to-end mapping and preserve the public method signatures.** Plugins already interact with the inline state; additional internal bookkeeping may accompany the mapping.
- **Keep cache lookup constant time and store at most one current cached answer per starting position.** Lookahead caching exists to keep repeated scans of difficult input affordable.
- **Add no dependencies and do not change `package.json` or `package-lock.json`.** The existing parser and test tools are sufficient.

## Out of Scope

- Invalidation after changing the source, environment, rule configuration, or nesting context on an existing state.
- Redesigning the separate backtick-run cache or changing Markdown delimiter syntax.
- Changes to the recursion-limit fallback or recovery from exceptions thrown by plugin rules.

<!-- devlyn:verification -->
## Verification

- `PATH=/Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/markdown-it/node-bin:$PATH npm test` exits 0. It runs the configured lint, build, type checks, CommonMark tests, library tests, and build tests. The added library tests cover a cached full-range code span followed by a narrower lookahead on the same state, silent state preservation, and reuse within an unchanged range; the existing suite covers ordinary parsing and pathological inputs.

Range histories and cache-validity semantics beyond those exercised by the suite remain source-review obligations. No additional standalone lint or type command is needed because `npm test` runs both and propagates their failures.
