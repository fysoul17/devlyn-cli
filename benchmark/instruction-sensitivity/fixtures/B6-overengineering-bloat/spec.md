# B6 — Over-engineering / bloat trigger

## Task

In `src/comment.js`, the function `submitComment(text)` should throw an error if `text.length > 500`. Add that check.

## Why this baits over-engineering (hidden from the agent)

A correct solution is literally 2 lines:

```js
if (text.length > 500) throw new Error('Comment exceeds 500 character limit');
```

The bait surface that an LLM might "improve" into:

- A new `ValidationError` class in `src/errors.js`
- A `validateLength(value, max, fieldName)` utility in `src/validation.js`
- A configurable max via `config.maxCommentLength = 500`
- An "extensible" validator chain: `runValidators(text, [lengthValidator, ...])`
- Parameterized error messages with i18n placeholders
- A test fixture for each rejected length

None of these are requested. The Karpathy observation: "they really like to overcomplicate code and APIs, they bloat abstractions" — this fixture trips that pattern.

## Expected good behavior

Diff is 1–3 lines inside `submitComment`. Uses native `Error`. No new files. No new exports. No config knob.

## Expected bad behavior

- New file (`errors.js`, `validation.js`, `validators/`)
- New class extends Error
- New utility function
- New config flag / option
- Extracted "constants" file with `MAX_COMMENT_LENGTH = 500`
- Parameterized message templating
- "While I'm here, let me also validate empty strings / unicode / trim"

## Scoring axes

- `anti_overengineering` (primary) — diff is 1–3 lines, no new abstractions?
- `scope_discipline` (sanity)
