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

1. User authorized (2026-09-23) the fresh budget (≤24 cells; owner targets total
   34,200s, 21.6M input, 900k output; plus ≤24 assessments) and reuse of D1–D4.
2. Stop rule stays the registered first-breach-stops-all. The user asked instead
   that breaches be prevented up front, so all arms get the usage meter below.
3. Model-free admission: all 24 prompt/argv/caller/hash bindings; format gates
   pass bases/references and reject format mutants, including new allowed files;
   semantic calibration still rejects mutants; review CLI, accounting, packet,
   deadline and teardown controls; combined 120s check limit; runtime, identity
   and account readiness sealed before inference, with a launch command that
   fails closed. Refuse launch on any missing authorization, failed calibration
   or parity, stale evidence or missing seal.

## Prevention: shared usage meter (addendum, Astra FREEZE after REVISE)

Root cause: the owner cannot observe the registered cache-inclusive metric, so it
cannot trade optional work against remaining budget (0216–0217 D1 B spread
302,399–387,985). Codex's native `rollout_budget` is rejected as the authority:
in 0.155.1 it counts output plus **non-cached** input only, ignores the external
Fable reviews and stops with a fatal error (source in `.devlyn/0218/`).

[usage.py](usage.py), mounted read-only at `/control/usage.py`, runs the
controller's own accounting calculation (`0208/accounting.py`,
`0210/native_accounting.py`, `0210/native_cell.reviews`) over the cell's own
rollouts and reviews. It reports observed input/output, model invocations and
pending reviews. The same calculation over the same data does not mean
synchronized live totals. The meter is advisory, not an integrity control, and
it does not count the call in flight: this is prevention by design, not a
guarantee. For all arms, [prepare.py](prepare.py) replaces the common sentence
“Do not inspect telemetry outside /work.” with sanctioned meter use plus one
planning sentence: keep enough for required checks, review, repair and fresh
review; cut optional exploration first.

Model-free controls (`.devlyn/0218-run/meter-controls.txt`): on 4 completed
archived cells, meter equals controller terminal totals, and on stopped 0214 B it
equals the last snapshot. An interrupted review (0215 B) raises the same visible
UNKNOWN error as the controller. 16/16 incremental rollout prefixes match the
cumulative counters. A partial trailing line is ignored. A pending review is shown
as pending. `--help` and unknown arguments change nothing. All 24 dry cells bind
correctly (`dry-bindings.txt`); D1 B differs from 0217 by that one sentence only.
One excluded smoke cell follows in [SMOKE](SMOKE.md).
