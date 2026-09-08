# 0136 — Keep installed helpers out of customer Ruff discovery

## Observed failure and decision

The0135 public Click preparation caught a customer-facing installer defect before any model launch. On upstream6aabf099, locked Ruff0.15.9 `python3 -m ruff check --no-fix .` passes. After the normal3.0.0 installation from53e6e92, the same command reports1396 errors, all in16 installed `.claude/skills/_shared/*.py` files. Original Click source/tests and task files produce none. Raw before/after evidence lives in `.devlyn/0135-public-issue-baseline-r0/` and `.devlyn/0135-root-preflight-r0/`.0135 remains NOT_LAUNCHED; no native result or quality/time comparison exists to rescue.

The violated invariant is ownership: the customer's recursive language checks discover bundled devlyn runtime code and apply customer style rules to it. Removing that code would break installed phase helpers; rewriting1396 unrelated lines or narrowing the customer's command would miss the cause. Use the smallest existing-tool boundary: a nested Ruff configuration in the managed `_shared` directory. Existing recursive packaging/installation can distribute it; no installer branch, customer configuration change, new dependency or general linter framework is needed. Principles: No workaround, No overengineering, No guesswork, Production ready, Optimized.

## Prospective acceptance

Before changing source, predict that the scoped nested exclusion restores the unchanged recursive Ruff command on a separately prepared installed Click checkout. Preserve0135's original installed WORK and raw failures. A deliberate undefined name in each of customer source, customer tests and a sibling custom skill must still be reported; the exclusion must not spread to those files. Restore only owned injected controls after preserving their results. Ordinary pytest, configured type checks and read-only formatter behavior must remain valid on the original Click source; the original Click issue remains unfixed by this installer repair.

Use an actual npm package and the normal owned-home installer. Verify packaged/source/installed boundary bytes, existing customer parent Ruff configs and sibling custom files, and repeat installation without changing them. Existing installer-managed settings behavior remains its current contract; compare the preserved customer fields and post-first-install bytes rather than falsely claiming the installer makes no settings changes. Run `bash scripts/lint-skills.sh`; keep all existing devlyn helper tests and customer rules active. No Click business patch, customer AGENTS.md/CLAUDE.md research text, runtime role/default change, upstream contact, npm publication or tag.

Ruff's ordinary hierarchical discovery is the scope. Explicit `--config`, `--isolated`, and explicitly named helper files can bypass normal discovery; do not claim interception of arbitrary lint commands. This iteration fixes demonstrated installation interference, not generic formatting quality or whole-harness superiority.

## Review and closure

Root owns implementation and final acceptance. Obtain one bounded actual Fable5.1 and one Grok4.6 source advisory on the final small candidate and retained validation using existing callers; opinions are not a unanimity gate. Keep actual context/availability/effort limitations and original output without retry or claiming unavailable advice. Commit and push verified source and concise research closure. Any later ordinary task execution needs its own prospective registration and cannot relabel0135.
