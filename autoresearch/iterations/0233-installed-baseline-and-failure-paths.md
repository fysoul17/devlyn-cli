# 0233 — the installed 4.2.0 baseline against bare, and the first lazily loaded method

2026-10-07. **Status: FROZEN 2026-10-07, before any measured, smoke or screening cell.** Astra's freeze review: round 1 REVISE (four blocking apparatus findings), round 2 REVISE (two), round 3 FREEZE-WITH-FIXES (one mechanical fix, applied with its regression test); records `0233-freeze-a{1,2,3}-*` beside the design dialogue. Any later change is a dated addendum at the end. Authors: root (Claude Opus 5.5) and Astra (gpt-6-astra, reasoning ultra, read-only). The design dialogue is `aud-a1-*` and `aud-a2-*` in `/Users/aipalm/.local/share/nx01/core-continuation-20260912/.devlyn/bundle/`.

## 1. Owner direction (2026-10-07, original words)

"지금까지 4.2.0 진행했는데, 우리의 원래 의도 목표 비전 북극성 등에 맞게 잘 구현되었는지, resolve도 없애고 했는데 속도는 빨라지고 모델들의 잠재력들은 bare 대비 solo/pair가 더 좋아졌는지, 아니라면 claude.md 나 agents.md 등에 lazy load 로 관련 소프트웨어 엔지니어링 기법들을 추가해서 필요할때마다 로딩을 하거나 해서 속도, 효율, 품질을 유지하고 모델들/에이전트들의 잠재력을 극대화해서 끌어내야 하거든. 어때? 점검해줘. astra ultra와 함께 심도있게 논의하면서 분석하고 개선이 필요하면 진행하고."

## 2. Audit result (root and Astra, converged)

- **North Star fit.** 4.2.0 conforms to the product shape the owner approved on 2026-10-05 (NORTH-STAR block; [0232](0232-harness-ladder.md) §8): the installed block carries the principles, ideate is the loop designer, resolve and design-ui are retired. Its outcome advantages are unproved: the installed baseline has never been measured against bare (HANDOFF "Next" 2), and the product has no pair policy (`devlyn-engines` keeps only the executor pin). Verification exists at the delivery reference (`_shared/task-completion.md`, "Review the resulting candidate diff and verify that candidate") and in ideate's acceptance, so direct-work verification depends on reaching delivery; behavioral coverage and independent review are unproven.
- **Speed.** 0232 compared native A with 4.1.0 F; A had no devlyn installation, so 0232 does not measure 4.2.0. The pipeline that made F 6.2× (claude) and 13.3× (codex) native wall per success is gone, but 4.2.0's end-to-end cost, including its restored default delivery, is unmeasured. The 2026-10-07 direct smoke predates the restored delivery default and ran no tests.
- **Evidence for the lazy-load proposal.**
  - Always-loaded text helps on some traps and can hurt (0223: DB-silent-catch none fails 2/2 on all four models, the old block 0/4 on opus; the deletion-only slim block failed B5 on sonnet 2/4 and astra 3/4, where none passed).
  - Review: 0184's repair gain came from fresh same-model review (2/4 → 4/4); other-model review stayed 2/4. 0229 found one Claude-only and one Codex-only hit on fixed source. In 0232, rung I's reviews found nothing on D3 (4 cells) and D4 (2 answered, 2 killed at session end); on I0185 they found real defects, I's trees carried 5 witnessed defects against A's 12 and F's 12, but I's I0185 input was 4.29× A's on claude and at least 8.86× on codex, and one review→repair produced a masking retry (claude `heldout` FAIL on both trees). K5 predates review (m24's first review input already creates the destination before the lock).
  - Failure-path class: A's two claude D4 failures are both "Timeout/error probes must terminate owned writers and readers"; A's I0185 trees carry K1/K2/K4 8 times in 12 defects; F carries the same classes.
- **Conclusion.** Generic engineering text is not the lever (engines already know it); a short method read at the moment it applies, licensed by an observed failure class, is the candidate. Review (pair or fresh same-model) is a later rung, licensed by defects that survive the cheaper method.

### Descriptive preview (2026-10-07, run after §10's predictions were written; not part of the registration)

A tiny direct task ("Add an add(a, b) function to calc.py, with a unit test in test_calc.py, and run the tests.") in fresh scratch repositories with no remote, `claude -p --dangerously-skip-permissions --model claude-opus-5-5`, the owner's real user configuration, 3 runs per arm, alternating (`scratchpad/speed/run.sh` in root's session):

| Arm | Wall s (median, range) | Turns | Input (cache counted once) | Output | Outcome |
|---|---|---|---|---|---|
| bare | 17.9 (15.1–18.7) | 3, 3, 3 | 97.2k–97.5k | 483–690 | tests pass; edits left uncommitted |
| 4.2.0 installed | 40.9 (40.0–52.1) | 8, 8, 11 | 319.7k–422.7k | 2.8k–3.2k | tests pass; `LOCAL_ONLY` commit; delivery worktree and branch removed; clean checkout |

The difference is the default delivery route (here the no-GitHub-origin fallback). It does work bare leaves to the user, so this is not a quality comparison; it measures what the default costs on a small request. With a GitHub origin, push, PR and merge add to it.

## 3. Question

Per configuration (claude, codex):
1. Does the installed 4.2.0 product (B) beat bare (A) under 0232 §6? This is the installed-baseline registration HANDOFF "Next" 2 promised.
2. Does one lazily loaded method (C = B + a failure-path pointer and file) beat B and A under the same rule?

## 4. Arms

| Arm | Installation | Prompt |
|---|---|---|
| A | none | native (0232's A) |
| B | 4.2.0 at `dd4957775337e597f39838fa73acd5c7ec4a5699`, its own installer offline | native |
| C | `candidate/0233-c-failure-paths` at `639fbac564db89db6dd99129f5f8ebc12916c5b8`: B plus one Quick Start line and `config/skills/_shared/failure-paths.md` (frozen text below) | native |

C's sole delta (frozen before any fixture adaptation or run):

> - Failure paths — before changing persistence, filesystem, locking, or process/thread behavior, including in tests, read `_shared/failure-paths.md` in `.claude/skills/` or `.agents/skills/` (project, else `~`).

```markdown
# Changes that hold state or resources

Before editing, use the request and affected code:

1. Identify protected state, owned resources, and the success or commit
   boundary, if any.
2. For applicable errors, timeouts, cancellation, competing operations,
   retries and target aliases, determine the required combination of
   restoration, recovery-data retention, release and error reporting.
   Preserve existing guarantees; do not invent new ones.
3. Order mutations and cleanup accordingly. Acquire required ownership
   before mutation; release only what you own. Recovery must not hide
   a failure the contract requires reporting.
4. Test the relevant failure transitions and assert their state and
   resource outcomes. Bound test waits and terminate or join test-created
   workers. Remove owned disposable resources when safe; retain and
   report required recovery data or unresolved cleanup.
```

Any behavior-changing revision of C starts a new candidate and a new registration.

## 5. Tasks and panels

| Panel | Tasks | Role |
|---|---|---|
| Development (exposed) | D3, D4, I0185 (0222), B5 (0223 drift probe, oracle on the final tree) | regression and development evidence |
| Confirmation (unused in designing C) | F10 `persist-write-collision`, F11 `batch-import-all-or-nothing` (May fixtures, adapted) | only if eligible after screening |
| Easy | E1 (negative trigger control: `--shout` output flag), E2 (positive trigger control: `config unset` on a config-writing command) | overhead tripwire |

Declared adaptations: I0185 loses the sentence "The root research owner handles local-only experimental delivery." (all arms); F10/F11 evaluator scripts move out of the participant tree, express is vendored into the base commit, and each contract inconsistency is listed in `experiments/0233/DESIGN.md`; B5's helper-removal row reads the final tree, fixing 0223's over-match.

F10 and F11 are graded only on what their participant request states: F10's rows check the persisted list (originals unchanged, each posted item present exactly once, numeric ids unique across the whole list, a fresh server process serving it) and accept any 2xx success response, because the request names no status or body; F11 accepts an empty batch (`201 {inserted: 0}`) and its mid-batch row also probes an invalid `qty`.

F10 and F11 history: May's headroom screen rejected both for pair lift (F10 bare 75 / solo 94; F11 bare 98 / solo 97), and F11 appeared in July ceiling work. They are described as tasks unused in designing C, not unused tasks.

## 6. Environment

As 0232 (image `devlyn-0231`, pinned CLIs, routes, models cache, watchdogs, assessors, usage accounting), except: every arm's anchor has a plain local-path `origin` (no GitHub URL). B and C's implicit delivery therefore takes the documented local fallback (`LOCAL_ONLY`), exercising allocation, transfer, acceptance, commit and reconciliation but not push, PR or merge. Results describe installed-default behavior in a local-origin environment, not real GitHub delivery cost.

A `codex exec` or `claude -p` session an owner starts through its shell is an owner-launched session, in every arm alike: its usage is counted once (missing accounting is a named gap), its engine, model and effort are reported, and its model never stops the cell; the owner's own identity check is unchanged.

The snapshot is the submitted source, arm-neutrally: a task-bound accepted commit when a task-complete receipt binds one; otherwise the live tree whose product differs (anchor first, else the one changed linked worktree); ambiguity is a locator STOP.

## 7. Decision rule

0232 §6, unchanged in substance, applied per configuration and per panel to three comparisons: B vs A, C vs B, C vs A. C is admitted in a configuration only if C vs B and C vs A both pass on the development panel and the confirmation panel does not fail.

Confirmation operates per configuration over that configuration's eligible tasks and judges C only (B vs A there is reported, never gating). It is `FAIL` when any quality condition (safe, completion, rows, severe) fails for any task in C vs B or C vs A, when either comparison fails, or when C completes nothing while B or A completes something; `PASS` when both comparisons pass; `UNCONFIRMED` otherwise, a clean all-zero panel included; `NO_HEADROOM` when no task is eligible. Admission is labeled `C` after a passing confirmation and `C-unconfirmed` after `UNCONFIRMED` or `NO_HEADROOM`. Panels are never pooled. Easy-panel results are reported per arm; a C completion regression there, or C raw wall/input/output above 1.25× B, is a reported tripwire. Unknown usage stays UNKNOWN.

**Confirmation eligibility (frozen before screening):** a confirmation task is eligible in a configuration if, across that configuration's four screening cells (A and B × 2), at least one cell fails product completion or at least one oracle row. Screening cells never enter a sum; confirmation uses fresh cells.

## 8. Diagnostics (reported, never in the rule)

`guide_read` (whether and when C's file was read relative to the first edit; `read` needs a successful content read, otherwise `mentioned`), `delivery_read` (whether `task-completion.md` was read and `task-complete.py` ran), and the pre-registered applicability below.

| Task | C should activate |
|---|---|
| D3 | ambiguous (changes how arguments reach a spawned process) |
| D4 | yes (FIFO IO; test writers and readers) |
| I0185 | yes (filesystem and locking) |
| B5 | no |
| F10, F11 | yes (persistence) |
| E1 | no |
| E2 | yes (config file writes) |

## 9. Cells and order

SMOKE 6 (outside sums) → development 48 → easy 12 → screening 16 (outside sums) → confirmation up to 24. Screening only gates confirmation, so it runs after the development and easy panels, which answer B vs A and C vs B sooner. Within a panel, each (task, configuration) block runs A, B and C back to back. The arm order of a block is the permutation at index (task position + 2 for codex) in `generate_cells.py`'s list of the six orders; replicate 2 reverses the block order and each block's arm order. Every development configuration sees all six orders, but positions are not perfectly balanced: in claude, C runs first, middle and last 2/4/2 times against A's and B's 3/2/3. Cell files are frozen in `experiments/0233/`. No other model-heavy work runs during measured cells.

## 10. Predictions (before any run)

**Root:**
1. **Activation.** C reads the guide before the first relevant edit in at least 75% of D4, I0185 and E2 cells in each configuration; in D3 between 25% and 75%; in B5 and E1 at most 1 cell of 8 combined.
2. **Delivery.** B and C read `task-completion.md` and run `task-complete.py` in at least 70% of cells whose request changes files, adding 60–180 s per such cell against A.
3. **Completions (development, 8 cells per arm and configuration).** claude: A 3–5, B 4–6, C 5–6; codex: A 5–7, B 5–7, C 5–7. No arm completes I0185.
4. **Quality.** C has fewer witnessed I0185 defects than B in each configuration and passes D4's teardown obligation at least as often as B; C's I0185 oracle rows are at least B's.
5. **Costs.** B's raw development wall is 1.1–1.4× A's and raw input 1.2–1.6× A's in each configuration; C's raw wall and input are within 0.95–1.2× B's.
6. **Decisions.** B vs A passes in claude with p ≈ 0.25 and in codex with p ≈ 0.10. C vs B passes in claude with p ≈ 0.35 and in codex with p ≈ 0.15. C admitted (both comparisons) in at least one configuration with p ≈ 0.25.
7. **Headroom.** F10 is eligible in claude with p ≈ 0.55 and codex p ≈ 0.45; F11 claude p ≈ 0.30, codex p ≈ 0.25. A task ineligible in a configuration is recorded `NOT_RUN` there; a configuration with no eligible task has `NO_HEADROOM` confirmation and any admission there is labeled unconfirmed (§7); replacement confirmation tasks need their own registration.

Root's arithmetic corrections, made at the freeze review before any run (no prediction changed in substance): in 1, B5 and E1 have 6 cells combined, not 8, so the bound is at most 1 cell of 6; in 3, no I0185 completion caps a configuration's development completions at 6, so codex's ranges read A 5–6, B 5–6, C 5–6; in 7, the consequence sentence now states §7's per-configuration rule, which the code already implemented.

**Astra (A2):** C will activate readily on D4/I0185, may improve some failure rows, and will have a harder time earning both token inequalities than demonstrating defect reduction; F11's headroom is the weak point.

**Astra (freeze review, before any run; `0233-freeze-a1-astra.out.md`):**
1. **Activation** (C reads before the first relevant edit, claude / codex): D3 1/2, 1/2; D4 2/2, 2/2; I0185 2/2, 2/2; B5 0/2, 0/2; each eligible confirmation task 2/2, 2/2; E1 0/1, 0/1; E2 1/1, 1/1.
2. **Delivery** (development cells reading the delivery reference and running the helper, A/B/C): claude 0/8, 8/8, 8/8; codex 0/8, 7/8, 7/8; 45–120 s added per installed delivery on claude, 45–150 s on codex.
3. **Development completions of 8** (central, range): claude A 4 (3–5), B 4 (3–5), C 5 (4–6); codex A 6 (5–6), B 5 (4–6), C 6 (5–6); no I0185 completion anywhere.
4. **Quality.** C's witnessed I0185 defects about 0.75× B's per configuration; p(strictly fewer) 0.65 claude, 0.55 codex. D4 teardown passes A/B/C: claude 1/2, 1/2, 2/2; codex 2/2, 2/2, 2/2. p(C's I0185 oracle rows ≥ B's) 0.75 claude, 0.80 codex.
5. **Raw development cost ratios** (wall, input, output): claude B/A 1.35, 1.60, 1.50; C/B 1.08, 1.10, 1.08; codex B/A 1.20, 1.35, 1.25; C/B 1.08, 1.10, 1.10.
6. **Decisions** (claude, codex): development B/A PASS 0.15, 0.05; C/B PASS 0.35, 0.25; C/A PASS 0.15, 0.08; admission including unconfirmed 0.10, 0.05; in at least one configuration 0.15.
7. **Headroom** (claude, codex): F10 eligible 0.60, 0.45; F11 0.30, 0.25; neither eligible 0.30, 0.45.

## 11. Honest limits

- Two replicates; exposed development tasks; an observational admission screen, not proof of broad superiority.
- Local-origin delivery is not GitHub delivery.
- The easy panel has one replicate: a tripwire, not an overhead estimate.
- Results hold for the pinned CLIs, image, routes and tasks.

## Addendum 2026-10-07 — SMOKE passed; measured run started

SMOKE ran on the frozen apparatus `dba55640` (control manifest `ba88ff9b5072c182d64f0293869e0d88357a1cc07e396467de100efaa0c784d`; packages B `6f03f5ac…`, C `2a8fb2de…`). Venue: Claude account fingerprint `9f2f3a391923`/`ea65f3b4f086` (a different account from 0232's two; `claude_max`, `default_claude_max_20x`) and the host Codex login; image, CLIs and models cache as 0232.

- **Identity** MATCH in 6 of 6 cells; **teardown** CLEAN in 6 of 6.
- **Snapshots**, one per cell: `changed-product` for both A cells and codex B and C; `receipt` for claude B and C, whose `LOCAL_ONLY` delivery bound an accepted commit.
- **Usage** COMPLETE in 5 cells; `smoke-codex-B` is PARTIAL with one named gap, a Codex inference started without completed usage (0232's known limit).
- **Reported behavior, not a criterion:** claude B and C read the delivery reference and ran `task-complete.py` (allocate, complete); codex B and C read it and did not deliver. C's guide was not read; SMOKE changes no state, so that is expected.
- As in 0232, every SMOKE product is PRODUCT_INCOMPLETE, because the assessors cannot confirm the SMOKE task's native-subagent obligation; SMOKE requires neither product success nor compliance.
- Owner wall, A/B/C: claude 34/103/68 s; codex 50/74/59 s.

The measured drive started at 2026-10-07T11:47Z (first seal of `d01-D3-claude-A-r1`) in the registered order (development, easy, screening, confirmation).

## Result 2026-10-08

All 84 measured cells finished (development 2026-10-07 21:51Z; easy, screening and confirmation 2026-10-08 04:31–09:46Z). Raw per-cell table, judgments, witnesses and `decision.json`: [results](../experiments/0233/results/).

**Decision (decide.py):** `0233:claude=B/A:FAIL,C/B:FAIL,C/A:FAIL,conf:FAIL,adm:none;codex=B/A:FAIL,C/B:FAIL,C/A:FAIL,conf:FAIL,adm:none`. C is not admitted in either configuration; nothing ships.

| config | panel | A | B | C |
|---|---|---|---|---|
| claude | development (D3, D4, I0185, B5 ×2) | 4/8 | 2/8 | 5/8 |
| claude | confirmation (F10, F11 ×2) | 3/4 | 1/4 | 2/4 |
| codex | development | 5/8 | 6/8 | 6/8 |
| codex | confirmation | 1/4 | 3/4 | 3/4 |
| both | easy (E1, E2) | 4/4 | 4/4 | 4/4 |

Raw completion counts; decide.py's outcomes also apply adjudications, false completion and witnessed defects. Quality conditions decide every development and claude confirmation FAIL; codex confirmation C/B fails on wall per success, and the easy-panel comparisons (reported, never gating) fail on resources alone:
- claude B/A: D3 and D4 completion, D4 safety (false completion d09) and severe, I0185 safety (false completion d36), rows and severe; every per-success resource test fails. Confirmation B/A fails on F10 completion.
- claude C/B and C/A: I0185 rows (`terminal-alias` C 0/2, B 2/2, A 1/2) and witnessed defects; C/A also D4 completion (C 1/2, A 2/2). C/B passes confirmation; C/A fails it on F10 completion (C 0/2, A 2/2).
- codex: I0185 witnessed defects decide B/A, C/B and C/A on development; confirmation B/A passes, C/B fails on wall per success, C/A is inconclusive (usage).

**Judgments** (root, prepared by a Claude workflow, verified by Astra): 84 audited; false completion 2 (`d09-D4-claude-B-r1`: "Every blocking call has a 10-second limit" while its test opens the FIFO unbounded on the main thread; `d36-I0185-claude-B-r2`: the lock-before-mkdir claim falsified by `i0185-mkdir-before-lock`, 0232 m24's standard); user-data harm 0; 37 severe findings in 13 cells with 10 witnesses (0232's I0185 witnesses reused and rerun, new D4 and I0185 witnesses added); 3 NOT_TRIGGERED rows adjudicated. Astra: severe REVISE (one unsupported non-binding rationale) → fixed → SHIP; audit REVISE on d35 → root kept "no" (its claim is contradicted only by a fault-injection witness, coverage under the m15/m22/m32/m33 line).

**Diagnosis (root and Astra, from finals and transcripts).** Claude with 4.2.0 often accepts passing visible checks plus a reported limitation as completion when the limitation breaks an explicit contract: D3 B bypasses the public `parseOptions()` override and its report discounts the regression because no known caller relies on it; D4 B reasons wrongly about bounded cleanup; F10 B and C both leave Express's default parser error in place ("I didn't add a JSON error handler because the request didn't ask for one", C-r2), while A handled it in both replicates. C's guide was read and did not change that decision. Candidate cause, to be tested alone: the operational definition of done in the shipped principles (line 25: done when nothing more can be removed "without breaking a learned failure mode"), which undervalues stated contracts not yet seen broken.

**Run notes.** Venue: the host Claude login changed twice (2026-10-07 13:20Z and 2026-10-08 ~02:05Z, outside the run); the owner approved continuing on the current account each time and `runtime.json` records the history; models, routes and pins did not change. Operator holds: root's ideate smoke overlapped measured cells once and was rerun under HOLD; disk shortage from other sessions held starts (never a running cell). Inputs: the run worktree lacked `.devlyn/0185` (d13) and `node_modules/qs/dist/qs.js` in E1/E2/F10/F11 (ignored by the sources' `dist` rule); both were restored byte-identical and every seal verified before dispatch; the stopped cells had dispatched nothing. The host Claude token was refreshed in place between cells, never during one.
