# F5 — Notes

## Purpose

The suite's FIX LOOP stress test. The tests are intentionally constructed so
the obvious first-pass implementation (simple `input.split(' ').filter(w => w === word).length`) passes the basic count case but fails on:

- Case insensitivity (`Cat` should match `cat`).
- Whole-word boundaries (`cat` should NOT match inside `category`).
- Empty-stdin edge (returning `undefined` instead of `0`).

Variant's pipeline is expected to:
1. BUILD produces a first implementation.
2. BUILD GATE runs `node --test`; some tests fail.
3. EVAL emits findings with `criterion_ref` pointing at specific failing cases.
4. FIX LOOP round 1 targets those findings and converges.

Bare, without a forcing mechanism, often ships the first implementation and
calls it done. Verification catches that.

## Failure modes detected

- **Partial implementation.** Naive token split without regex word boundaries.
- **Case handling.** Missing `.toLowerCase()` on both sides of the comparison.
- **Async stdin.** Using `process.stdin.on('data')` without handling `end` properly → program hangs on test invocation.
- **Forgotten empty case.** `stdin.read()` returning `null` → `null.length` or `undefined` output.

## Pipeline exercise

- **Phase 2 EVAL** is the star: it must identify each failing test case with file:line evidence.
- **Phase 2.5 FIX LOOP** runs at least once. A fixture passing with 0 fix rounds is a smoke signal that the test-trap design is too lenient; inspect.
- **Phase 1.4 BUILD GATE** uses `node --test` which exits non-zero on any failure, forcing route to 2.5.

## Current status

Rejected as pair-lift evidence. `20260512-f5-fixloop-headroom` measured bare
99 / solo_claude 99, with bare and solo each passing 5/5 verification commands.
It fails both headroom preconditions and should remain a fix-loop control unless
reworked.

## Rotation trigger

When fix rounds consistently = 0 across two shipped versions, the trap is too
easy. Stiffen by adding a fourth test edge (e.g., Unicode folding, hyphenated
words).
