# F2 — Notes

## Purpose

Canonical **medium-complexity single-file CLI task** in the suite. Tests the
middle-ground: a task big enough that first-draft implementations often miss
an edge case (EACCES vs missing-dir distinction, TTY gating, HOME guard),
small enough that every arm can plausibly finish in < 10 minutes.

## What failure mode does it detect?

- **Silent catches.** The pattern `try { readdirSync(...) } catch { return [] }`
  is a natural shortcut here. Bare prompt arms tend to take it. The pipeline's
  EVAL phase catches it as a `correctness.silent-error` or
  `hygiene.silent-catch` finding.
- **Edge-case distinction.** ENOENT vs EACCES must be reported differently.
  Arms that collapse both into a generic FAIL miss a spec Requirement.
- **Over-engineering.** Since v3.6's CRITIC calibration, hand-rolled
  mode-bit writable checks are blocked in favor of `fs.accessSync(...,
  fs.constants.W_OK)`.

## Which pipeline phases does it exercise?

- Phase 0: routing — `permission`, `env` risk keywords in the task body
  escalate to `strict`.
- Phase 1 BUILD: main implementation pass.
- Phase 1.4 BUILD GATE: `node --check` syntax gate.
- Phase 2 EVAL: catches silent-catch trap if present.
- Phase 3 CRITIC design: applies stdlib-vs-hand-rolled calibration.
- Phase 3 CRITIC security (native): minimal — no deps changed.
- Phase 4 DOCS: spec frontmatter `status: done`.

## Why can't another fixture cover this?

- F1 is trivial (single-line edit, no edge cases).
- F3 is backend (different idioms, tests run differently).
- F5 is designed to force fix-loop (not applicable here).
- F7 is scope-creep (orthogonal concern).

## When should this fixture be retired or replaced?

When both arms score > 95 for two consecutive shipped versions — i.e., the
fixture saturates and no longer differentiates. Candidate replacement: a
similar-size CLI task with multiple interacting flags or a subcommand that
spawns a child process.

## Calibration history

- v3.4   skill 57 / bare 45 / margin +12 (gpt-5.3-codex judge)
- v3.4.1 skill 59 / bare 43 / margin +16 (gpt-5.3-codex judge)
- v3.5   skill 92 / bare 81 / margin +11 (gpt-5.4 xhigh judge) — huge absolute jump; bare silent-catch caught

Absolute scores jumped with the stronger judge. Margin stays solid (+11
after stdlib calibration is expected to open a few points more).
