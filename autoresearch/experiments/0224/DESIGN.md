# 0224 — structure screen: A, B′, C, F on I0185 and D4

2026-09-26. **Status: REGISTERED** (written before any screen cell is dispatched). Session 6 of [0221](../../iterations/0221-subtraction-direction.md) §4–§5 on the [0222](../0222/DESIGN.md) apparatus. This is a screen on exposed tasks: it decides only whether B′ and C continue to the Session 7 unexposed confirmation. It is not holdout evidence, and it cannot adopt anything.

## Cells and order

{I0185, D4} × {A, B′, C, F} × {claude, codex} = 16 cells, one draw each, in the order of [cells.tsv](cells.tsv). Configs alternate in pairs (claude, codex, codex, claude, …). Each arm appears twice in the first eight cells and twice in the last eight, and no (task, config) group runs all four arms in a row.

- **B′** is `/devlyn:intent` from the Session 5 merge `79532e97`, packed into control tree v2 (tarball sha256 `433cb672…`), installed like F and bound to the same `product_roles`. The B′ route smoke ([0222 SMOKE](../0222/SMOKE.md), Session 6 section) passed before this registration was frozen.
- The routes, watchdogs, evaluator, assessors, stop rules and verdict mapping are 0222's, unchanged. Owner wall is `owner_seconds` from the cell result. After a hang timeout (5400 s), the preserved product is evaluated like any other (0221 packet E1 §5); its wall is 5400 s.
- **OUTPUT** is the sum of output tokens over every model the cell recorded (owner result or rollouts, nested Claude results, reviewer calls). It is a lower bound whenever usage is PARTIAL.

## Before any rule is computed

1. **ADJUDICATE** (an I0185 replay row is NOT_TRIGGERED because its hook never fired): only that row is adjudicated, and every other row, check, scope result and assessment keeps its value. A cell with any other failure is PRODUCT_INCOMPLETE whatever the adjudication says. Fixed predicate per row: root writes a variant of that replay that moves only the injection hook to the product's equivalent step (cited file:line: the source copy for `alias`/`terminal-alias`, the owned-lock release for `release`, the second skill publication for `absence-lock`) and keeps every assertion byte-identical. The row is PASS only if the variant fires and passes. If the product has no equivalent step (for example, no lock at all), the row is FAIL. The variants and their outputs are recorded in RESULT.md before any cross-arm number is computed; nothing stays ADJUDICATE.
2. **Final-report audit:** root reads every cell's `final.txt` against its evidence. A **false completion** is a report that claims a check ran or passed, a requirement is verified, or (B′) a gate verdict, and the cell's own evidence contradicts it. A failing hidden oracle row does not make a false completion by itself, because the owner cannot see the oracle.
3. **STOP rows** follow 0222: root names the cause and fixes it, and the stopped row is kept as `<name>.stop-N`. The affected bundle is the stopped cell plus every cell whose *execution* the cause could have changed (the same prepare, install, control, image or dispatch path under the same route). That bundle is re-dispatched, with its original rows kept. A fix that changes only grading (identity, usage, evaluator) re-evaluates the already-verdicted cells from their preserved evidence and does not re-dispatch them. A cell is never re-dispatched because its product failed.

## Decision rules (per candidate X ∈ {B′, C} and config k, over both tasks)

- **loss(X, k):** on some task, A or F in config k is COMPLETE and X is not (0221 §4 criterion 2, at task level). Row-level losses (an oracle row or public check that A or F passed and X failed) are reported, not binding.
- **block(X, k):** an X cell in config k has a false completion, a scope violation, or a HIGH/CRITICAL defect that root reproduced with a failing check against its final tree (from an assessor or a Grok static check) (criterion 1).
- **signal(X, k)** needs one of two things:
  - quality: on some task, X is COMPLETE and A is not;
  - efficiency: on some task where X and F are both COMPLETE, X's wall ≤ 0.7 × F's wall, or X's OUTPUT ≤ 0.7 × F's OUTPUT when X's usage is COMPLETE. F's OUTPUT is always a lower bound, so the comparison stays valid.
- **X continues in config k** iff signal ∧ ¬loss ∧ ¬block. Otherwise X stops in k.
- **Coupling (0221 §4):** if B′ continues in k, C also continues in k unless block(C, k). If neither B′ nor C continues in any config, Session 7 does not run, and Session 8 takes the candidate-close branch (full stays). B′ stopping never, by itself, makes C adoptable (criterion 6).
- The outcome token is `SCREEN:B'=<continue configs|none>;C=<continue configs|none>`. Every rule input is reported beside it: per-cell verdict, wall, OUTPUT and completeness, and assessor disagreement.

## Grok static checks (4 calls)

- **Selection:** a repair episode is a candidate cell in which a reviewer returned a binding finding and a later source change followed it. B′ episodes are gate reviews with `binding > 0`; C episodes are `/control/review.py` calls with an actionable finding. Within a cell, the episode is the earliest such review by recorded time. B′ ties go to `primary_judge` before `pair_judge`; C ties go to the lower call number. Take the first B′ episode and the first C episode in dispatch order. If one arm has none, take the next episode from the other arm.
- **Fewer than two episodes:** each missing episode is replaced by two "find defects" calls, on the final product diffs of the next two candidate cells in dispatch order that no episode already used, alternating B′ and C. There are always four calls.
- **Per episode, two read-only calls to grok-4.7:**
  - the defect diff, which is exactly what that reviewer received: "find defects";
  - the repair diff, from the reviewed source to the final source on the allowed paths: "is the repair correct and complete, and does it add a defect?".
- Grok does not see the reviewer's findings or the arm. Root reproduces each HIGH/CRITICAL Grok finding against the final tree; a reproduced one counts toward block. An unreproduced finding is recorded and has no effect.

## Predictions (before dispatch)

1. Every cell gets a verdict, with no STOP row and clean teardown.
2. I0185: A is not COMPLETE in either config (0185: native Astra 0/2 on the lock-release/rollback class). In each config, at least one of B′, C and F is COMPLETE.
3. D4: at most one A cell is COMPLETE.
4. In every (task, config) group, F has the largest wall of the four arms. B′'s wall is ≤ 0.7 × F's in at least 3 of the 4 groups.
5. Every B′ gate run ends PASS or NEEDS_WORK, never BLOCKED.
6. The outcome continues B′ in at least one config, and C in at least one config.
7. At least one of the two Grok defect-diff calls names the defect class that the episode's reviewer found.

## Execution

`bash autoresearch/experiments/0222/screen.sh <runtime.json> autoresearch/experiments/0224/cells.tsv`, run serially under `caffeinate`. Runtime: control tree v2 (manifest sha256 `f51c73f2…`), image `84a01941`, and the same account fingerprints as the 0222 smoke. A `not-dispatched` exit (auth/account preflight) is not a verdict: fix the login, then resume. Usage is recorded after the fact; there is no budget. Raw evidence stays in the Session 6 completion scratch; RESULT.md holds the table, the adjudications, the audits and the token.
