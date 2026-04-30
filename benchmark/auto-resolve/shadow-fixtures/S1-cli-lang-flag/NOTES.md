# S1-cli-lang-flag NOTES

## What failure mode does this fixture detect?

**Spec-compliance precision under input-parsing pressure.** Bare LLMs handling unknown enum values tend to silently fall back to a default — the natural Node implementation pattern is `const greeting = greetings[lang] || greetings.en;` which would silently degrade `--lang fr` instead of erroring. The spec explicitly forbids that behavior; the trap is whether the implementation respects the precise output contract under user-input-parsing context.

## What pipeline phase(s) is this testing?

- **BUILD**: implementation must surface an error on unknown language, not silently fall back.
- **BUILD_GATE**: verification_commands match exact UTF-8 output literals for each language.
- **CLEANUP**: tests must be added; no other subcommand may be touched (scope discipline).

## Why can't another fixture cover this?

F2 has the silent-catch trap on a system-state subcommand (`doctor`). S1 puts the same trap shape in user-input-parsing context with multibyte UTF-8 output literals. Different surface category: F2 catches "filesystem error swallowing", S1 catches "user-input fall-through default."

## When should this be retired?

When two consecutive ship-gate runs show bare DQ rate ≤ 30% on this fixture — meaning bare LLMs have learned the pattern and the trap is no longer load-bearing as a categorical reliability signal.

## Mutation source

Direct mutation of `F1-cli-trivial-flag` (which adds `--name <name>`). S1 keeps the trivial-flag scaffold but adds:
- Multi-value enum (4 languages instead of 1 free-form name).
- Explicit error path on unknown enum (the fall-through trap).
- Multibyte literal output (UTF-8 Korean / Japanese / Spanish strings as exact-match contract).

The combination produces a categorical-reliability gate F1 alone does not provide.
