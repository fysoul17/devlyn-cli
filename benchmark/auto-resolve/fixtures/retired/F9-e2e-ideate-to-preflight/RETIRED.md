# RETIRED — F9-e2e-ideate-to-preflight

**Retired**: 2026-04-30 (iter-0033a)
**Replaced by**: `benchmark/auto-resolve/fixtures/F9-e2e-ideate-to-resolve/`
**Source SHA**: `8d4d57f` (commit before the 2-skill-contract rename).

## Why retired

The 2-skill redesign (Phases 1-3, iter-0029 / 0031 / 0032) replaced
`/devlyn:ideate` (greenfield) and folded `/devlyn:preflight` into
`/devlyn:resolve`'s VERIFY phase. The OLD F9 fixture's contract assumed
the 3-skill chain (`/devlyn:ideate` → `/devlyn:auto-resolve` →
`/devlyn:preflight`), which is unobtainable at HEAD post-iter-0032
because OLD ideate was deleted.

iter-0033a redesigned F9 to match the shipped 2-skill contract.

## When to consult this archive

- Replaying a regression suspected from the OLD chain.
- Migrating a pre-2026-04-30 historical run record back to readable shape.
- Auditing what changed when the new fixture's measurements diverge from
  pre-redesign baselines.

## What lives here

The exact file contents of the F9 fixture as of `8d4d57f` (the last commit
before the rename). DO NOT use this directory as a live fixture — it is
not picked up by `run-suite.sh`. Restore-and-run requires a manual copy.
