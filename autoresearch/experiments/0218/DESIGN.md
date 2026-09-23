# 0218 — D1–D4 A/B/C apparatus-corrected exploratory screen (design)

2026-09-23. User: continue to the D1–D4 A/B/C screen, designed with Astra.
Root direct, no resolve. Opus and Astra (gpt-6-astra/high, read-only) wrote
independent R0s; Astra returned FREEZE in round 1. Design only: nothing dispatched,
and launch needs the two user decisions below.

## What it is

A new, separately registered screen, not a resumption of the stopped
[0213](../0213/RESULT.md): “0206 as amended by [0210](../0210/AMENDMENT.md),
using exposed development material.” It uses the
[0206 protocol](../0206/PROTOCOL.md) single-redesign allowance and needs a fresh
budget. Kept identical: tasks, bases, scopes, obligations, byte-identical
`0204/owner.md`, the A/B/C distinctions, owner/reviewer identities and efforts,
order (D1..D4; A/B/C then C/B/A), two repetitions, and every per-task target.
All archives and historical verdicts stay as they are. Under 0210 results are
descriptive only: no advancement, confirmation, adoption or causal claim. Reused
D1–D4 can never serve as confirmation material.

## Apparatus (identical across A/B/C within a task)

| Task | Declared/evaluated checks added or changed |
| --- | --- |
| D1 | node checks prefixed `env -u NO_COLOR`; Prettier gate on the D1 allowed paths ([0216](../0216/DESIGN.md)) |
| D2 | pytest unchanged; `/control/ruff format --check --no-cache src/click tests` |
| D3 | node checks prefixed `env -u NO_COLOR`; `node /control/prettier/bin/prettier.cjs --check --no-error-on-unmatched-pattern lib/command.js tests/command.executableSubcommand.test.js tests/args.literal.test.js 'tests/fixtures/**'` |
| D4 | pytest unchanged; same Ruff command as D2 |

Every task keeps the [0214 waiting text](../0214/common-wait.txt) and uses the
[0217 review launcher](../0217/review.py): help never dispatches, unknown arguments
fail. Prettier 3.8.3 (commander lockfile, sha512 verified) and Ruff 0.15.9 (click
pre-commit pin, PyPI sha256 verified) are mounted read-only in `/control`. Owner and
evaluator run the identical format command; the evaluator conjoins it into
completion and assessment evidence. Checks, formatting and teardown share the
existing 120s allowance, so the 0216 evaluation wrapper must be replaced. No
lint or codespell gates: carry the observed formatting fix, not the whole
pre-commit suite.

Model-free prechecks (`.devlyn/0218/`): Click pytest is identical with and without
`NO_COLOR` (2,099 passed), so only Commander gets the prefix. D3 allowed paths
pass Prettier at base. At base, Ruff passes and ignores a misformatted `.devlyn`
helper, but rejects a new misformatted allowed test file. `--no-cache` is required
because the evaluator mounts `/work` read-only.

D1 is exposed tuning material: freeze the apparatus now, add no D1 pass-chasing,
report D1 separately and never pool the 0214–0217 diagnostics (0216 had an
accidental review hint; 0217 rep1 had a post-hoc seal).

## Before any dispatch

1. User authorizes the fresh budget (≤24 cells; owner targets total 34,200s,
   21.6M input, 900k output; plus ≤24 assessments) and the reuse of D1–D4.
2. Stop rule. Default is the registered first-breach-stops-all rule
   (0210: stops further spend when interrupted-call totals are uncertain). The
   alternative records a fully accounted breach as that cell's BUDGET_EXCEEDED
   and continues, so a D1 breach does not censor D2–D4. It would need a
   prospective amendment and proof of safe quiescence/terminal accounting;
   infrastructure, identity, lineage or usage failures still stop everything.
   It is enabled only by explicit user authorization.
3. Model-free admission: all 24 prompt/argv/caller/hash bindings; format gates
   pass bases/references and reject format mutants, including new allowed files;
   semantic calibration still rejects mutants; review CLI, accounting, packet,
   deadline and teardown controls; combined 120s check limit; runtime, identity
   and account readiness sealed before inference, with a launch command that
   fails closed. Refuse launch on any missing authorization, failed calibration
   or parity, stale evidence or missing seal.
