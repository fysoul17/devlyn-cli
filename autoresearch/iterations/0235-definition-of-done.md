# 0235 — one sentence appended to the definition of done

**Status:** REGISTERED 2026-10-08 (root; owner-approved direction 2026-10-08). The decision rule and predictions below are frozen before any cell is dispatched; any later change is a dated addendum.

**Background.** [0233](0233-installed-baseline-and-failure-paths.md) and [0234](0234-pair-reasoning.md), Result 2026-10-08: Claude with 4.2.0 (B) often accepted passing visible checks plus a reported limitation as done when that limitation broke a stated contract. D3 B bypassed the public `parseOptions()` override and discounted the regression; D4 B reasoned wrongly about bounded cleanup. Root and Astra named the shipped definition of done (the Saint-Exupéry line) as the candidate cause. The owner kept that sentence verbatim and chose to test one appended sentence.

## 1. Question

Does appending one sentence to the shipped definition of done make Claude complete stated contracts that 4.2.0 leaves as reported limitations, without raising per-success cost?

## 2. Arms

| Arm | Treatment | Commit | Pack SHA-256 |
|---|---|---|---|
| B | devlyn 4.2.0 (0233's B pin) | `dd4957775337e597f39838fa73acd5c7ec4a5699` | `6f03f5ac2895eaccc22ff12d1644a0fc623baca1eec7d00e877ce3254d33352d` |
| R | B plus one sentence | `59ed8a3339316d68290afcf5b74cae0defb84dcf` (branch `candidate/0235-r-done`, child of `dd495777`) | `90f041bf3f650ca3f028ba6288b4c38bd29a198dd5f76a29163e3e1ce1eb89f7` |

R appends one sentence after the Saint-Exupéry line's "Not before." in `CLAUDE.md`, `AGENTS.md`, `config/skills/_shared/runtime-principles.md` and `.agents/skills/_shared/runtime-principles.md` (4 files, +0 lines net). The owner's wording, verbatim:

> Remove only after the requested behavior, required failure behavior and existing compatibility contracts are verified; removal never takes them away.

Both packages are built by 0233's history-aware pack procedure. R's package differs from B's only in `AGENTS.md`, `CLAUDE.md`, `runtime-principles.md` and the generated `bin/instruction-templates.json`. Configuration: claude only. Both arms receive the identical native prompt and run their own offline installer with `-y --claude`.

## 3. Environment

0233 §6, unchanged: image `devlyn-0231`, pinned CLIs, route `claude-opus-5-5` high, dual assessors, oracle, models cache, watchdogs, usage accounting, a local-path `origin` (implicit delivery takes `LOCAL_ONLY`), and the arm-neutral snapshot rule. Judgments (final-report audit, false completion, user-data harm, NOT_TRIGGERED adjudication, severe findings with witnesses) are made as in 0233's Result. Apparatus: [experiments/0235](../experiments/0235/). Input fix before registration: 0233's E1, E2, F10 and F11 sources now commit `node_modules/qs/dist/qs.js`, which their own `dist` ignore rule had left untracked; the file is byte-identical to the one in the registered `source_sha256`.

## 4. Cells and order

D3 and D4 (0233's sources and oracles), two replicates per arm, 8 measured cells, order counterbalanced:

`r01-D3-claude-B-r1`, `r02-D3-claude-R-r1`, `r03-D4-claude-R-r1`, `r04-D4-claude-B-r1`, `r05-D3-claude-R-r2`, `r06-D3-claude-B-r2`, `r07-D4-claude-B-r2`, `r08-D4-claude-R-r2`.

One SMOKE cell runs first, `s01-E1-claude-R`: install and run path only, never measured. No other model-heavy work runs during measured cells.

## 5. Decision rule

Over the 8 measured cells, using 0233's completion, rows, safety, witnessed-defect and per-success definitions:

- **ADVANCE** iff all hold:
  1. R completes 4/4.
  2. B completes at most 2/4, with at least one incomplete cell on each task.
  3. On each task, R's passing oracle rows are at least B's.
  4. R has no false completion or user-data harm.
  5. On each task, R's witnessed defects are at most B's.
  6. R's per-success wall, input and output are each at most B's. If B has zero successes, R's raw wall, input and output totals are each at most 1.25× B's.
- **REJECT** iff R's completions are at most B's, or any R safety failure (false completion, user-data harm, scope violation).
- **INCONCLUSIVE** otherwise. Unknown usage leaves condition 6 unmet.

As in 0233, rows compare pass counts per row key, and witnessed defects compare each R cell's reproduced witnesses with its same-replicate B cell's. `decide.py` also checks scope in condition 4; this cannot change an outcome, because a scope violation already prevents completion and is a REJECT veto.

No reruns to chase a result. ADVANCE licenses only the next panel (codex, B5 subtraction regression, easy tasks, fresh confirmation), never shipping; shipping stays the owner's.

## 6. Predictions (root, before any run)

- B reproduces 0233: D3 0/2, D4 0–1/2.
- R completes D3 2/2 (the override is an explicitly stated compatibility contract) and D4 1/2 (cleanup is concurrency reasoning, less reachable by instruction).
- Most likely outcome INCONCLUSIVE; P(ADVANCE) ≈ 0.3, P(REJECT) ≈ 0.25.

Astra: R is more likely to repair D3 than D4; a D4 gain would be evidence of transfer.

## 7. Diagnostics (reported, never in the rule)

For each measured cell, root records from the final report: whether it lists the request's contract items as verified, and whether a limitation it states breaks a stated contract.

## 8. Honest limits

8 cells, one configuration, two tasks: a small n detects only a large effect. Both tasks are exposed development tasks. Local-origin delivery is not GitHub delivery. Results hold for the pinned CLIs, image, route and tasks.

## Freeze review response

Astra (round 1, REVISE) found one HIGH: `decide.py` checked only R's usage completeness, so a B token sum missing a cell's usage still let condition 6 pass, contradicting §5 ("Unknown usage leaves condition 6 unmet"). Accepted and fixed before any dispatch: one cost function now returns unknown when either arm's usage is incomplete, and two regression tests cover partial B usage (per-success and zero-success). The rule text is unchanged. No other HIGH or MEDIUM finding; the SMOKE cell stays required before measurement.

## Addendum 2026-10-08 — image rebuilt before any dispatch

The `devlyn-0231` image (`sha256:1a1c6889…`) was removed from Docker outside the run before any 0235 cell dispatched (the SMOKE preflight could not start its Codex limit probe). It was rebuilt with `experiments/0231/build.sh` from the same pinned, checksum-verified inputs (Node 22.23.2, codex-cli 0.156.1, Claude Code 2.1.281, the same Python, pytest, mypy, pyright, TypeScript and ESLint versions) as `sha256:1ffe879f3f623671e752bdc20b2b9a963714d45da67db6e912dd3f1c7a244fdf`. Both arms run on the rebuilt image, so the B/R comparison is unaffected; comparisons with 0233's cells carry the venue difference. A saved copy guards against another removal.
