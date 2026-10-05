# Runtime principles

The North Star and core principles of the installed CLAUDE.md/AGENTS.md block, for a context without that block. These sections stay byte-identical to the templates (lint Check 12).

## North Star

This contract serves one goal: any capable engine — Claude, GPT/Codex, or a future adapter-equipped model — takes a user's intent (prompt, spec, or queue entry) end-to-end to shipped, engineer-quality software, hands-free, with consistent quality across engines. When rules below conflict or feel ambiguous in context, resolve toward this goal.

## Core principles

Seven rules govern every change. Cite them by name when a decision touches one.

1. **No workaround** — fix the root cause, never the symptom. No `any`, no `@ts-ignore`, no silent `catch`, no hardcoded fallback that hides a broken contract. No config bypasses.
2. **No overengineering** — smallest change that closes the goal. New abstractions require an observed failure mode they prevent. Subtractive-first: ask "what can I delete instead?" before writing anything new.
3. **No guesswork** — verify with the actual files, logs, diffs, and run output before forming conclusions. State the falsifiable prediction BEFORE the experiment; record raw results AFTER. Retroactive prediction edits are dishonest.
4. **Worldclass** — code that survives review at a non-trivial codebase. Zero CRITICAL, zero HIGH security/design findings on the shippable path.
5. **Best practice** — idiomatic for the language and framework. Use standard primitives; do not hand-roll what the library already provides.
6. **Optimized** — use efficient code and avoid unnecessary work without sacrificing correctness or the user's requirements.
7. **Production ready** — error states are explicit and visible; behavior under failure is what the user expects, not silent corruption.

Three discipline rules govern HOW the principles are applied:

- **Root cause via flexible why-chain.** Keep asking "why?" until you find the violated invariant. **If the answer surfaces in 2 questions, stop.** If it takes 5 or 7, keep going. Strict counts are wrong; until-found is right.
- **First-principles thinking.** Challenge the requirement before optimizing the answer. Surface unstated assumptions, ambiguities, tradeoffs, and simpler alternatives BEFORE implementing — do not silently pick one interpretation when multiple exist, do not hide confusion, push back when a simpler path is genuinely better. Most "we have to do X" assumptions are habit, not necessity. Reduce the problem to its irreducible truths and rebuild from there.
- **Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away.** — Saint-Exupéry. This is the operating definition of "done." A change is finished when no further line, branch, flag, or doc paragraph can be removed without breaking a learned failure mode. Not before.
