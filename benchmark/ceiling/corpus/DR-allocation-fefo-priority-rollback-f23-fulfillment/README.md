# F23 ceiling corpus port

## Base construction

`source.bundle` is the committed pre-task state from
`benchmark/auto-resolve/fixtures/test-repo`. F23's `setup.sh` is empty, so no
fixture data is staged before the base commit. The bundle deliberately excludes
the source repository's `.git` directory and ignored `node_modules`: the task,
gold patch, and hidden oracle need only Node core modules and `node --test`.

## Classification

- Categorical-reliability class: **allocation/FEFO/priority-rollback**. The row
  composes global order priority, per-order rollback, distance-first warehouse
  selection, FEFO lot selection, and single-warehouse line feasibility.
- L3 classification: **ALGORITHM**. The hardness is the interaction among the
  public invariants, not a trigger phrase. `task.txt` therefore preserves the
  source fixture's complete public formal contract while omitting every hidden
  warehouse, order, SKU, lot, quantity, and date value.

## Oracle and gold choices

The hidden oracle embeds both source behavioral verifiers, runs the existing
CLI suite, adds public-contract-only coverage for validation, exact stream and
output shapes, ordering tie-breaks, single-warehouse rejection, remaining-stock
sorting, and input immutability, checks the two class-defining silent-catch
patterns, and enforces the visible `bin/cli.js` / `tests/cli.test.js` scope. The
broader linter-suppression disqualifier is intentionally absent per iter-0068
R-quality item (b). `hidden/reference.patch` implements the command and its CLI
tests without adding dependencies.
