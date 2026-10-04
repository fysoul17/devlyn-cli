# 0231 — live comparison: the 0225 bundle against 4.1.0

2026-10-04. **Status: DRAFT, not frozen.** Design: independent R0s (root; Astra gpt-6-astra/ultra, read-only), then R1 and R2. **Owner decision (2026-10-04):** eligibility with replicates compares counts per (task, config) ("통과로 봄 (Claude 추천)"); Astra's pairwise recommendation is recorded below. The run needs the owner's separate approval. Raw record: `.devlyn/bundle/live-r0-*`, `live-r1-*`, `live-r2-*`.

## Why

- The owner's goal behind [0225](0225-resolve-cost-cuts.md) ("Why"): cut full resolve's unnecessary time and tokens, with every review guarantee kept.
- 0225 "Release": steps 2–5 ship only as a bundle adopted in both configs.
- [0226](0226-verify-recall-screen.md):83: a live comparison of the bundle needs its own registration and the owner's approval to run resolve; 0225's approval does not transfer. HANDOFF forbids the 0225 live comparison itself, so this is a new registration, not its resumption.
- [0230](0230-bundle-steps-3-5.md) developed the bundle, whose head is `f71a17d3` (tree `2b300050`).
- **Owner direction (2026-10-04):** design now with Astra. A Claude review precedes the run, and the run needs a separate approval.

**0231 decides one thing:** whether steps 2–5 are adopted in both configs on three exposed tasks. It cannot establish holdout quality, non-regression on unexposed work, or any single step's effect.

## Arms

| Arm | Source | Notes |
|---|---|---|
| Control | `origin/main` at freeze (now `4056ebe2`) | Product files equal `f33cf2ca`'s; version 4.1.0. |
| Candidate | the bundle head at freeze (now `f71a17d3`) | Re-frozen by addendum after any later product change; no result carries over. |

- The result is attributed to the whole difference, never split per step. There is no step-6 arm.
- **Packing:** both arms come from their frozen commit by one procedure, the publish procedure in `publish.yml`: a clone with its history → `node scripts/update-instruction-templates.js` (it rebuilds `bin/instruction-templates.json` from first-parent history) → `npm pack --ignore-scripts`, in one environment. A plain `git archive` export would ship the stale committed `instruction-templates.json`, and the installer reads it to migrate existing instructions.
  - Recorded per arm: source SHA, tree SHA, tarball sha256, file list, installed-file list.
  - Check: the control tarball equals the published 4.1.0 tarball file for file (shown 2026-10-04 at `4056ebe2`), so the procedure reproduces publishing.
- **Install:** each arm's own installer runs offline in the cell image, and only the selected package is visible. The Claude config uses `-y --claude`, the Codex config `-y`.
- **Roles** come from 0222's `product_roles` and are bound by `--role-config /harness/roles.json` (`{"roles": …}`), a harness-owned file on the read-only `/harness` mount. Both arms accept it and rank it above project pins (`role-config.py`). A project `.devlyn/engines.json` would stay in the anchor when the owner allocates a linked worktree, so it is not used:

  | Config | Owner | IMPLEMENT | Primary judge | Pair judge |
  |---|---|---|---|---|
  | Claude | claude-opus-5-5/high | native Claude, inheriting the owner model | claude-opus-5-5 | gpt-6-astra/high |
  | Codex | gpt-6-astra/high, gpt-6-sol/high children | gpt-6-sol/high | gpt-6-astra/high | claude-opus-5-5 |

  Both arms' validators reject an explicit Opus 5.5 effort, so Claude judges are model-only. Claude's effective effort is reported as unverified.
- **Prompt:**
  - Claude: `/devlyn-resolve --goal-file .task/goal.txt --role-config /harness/roles.json --max-rounds 4`.
  - Codex: an instruction to read the installed `devlyn-resolve/SKILL.md` and execute the same command; the exact text is frozen with the apparatus.
  - **Goal file:** bootstrap accepts only a relative goal file inside the worktree (`resolve-bootstrap.py` `safe_goal_file`, both arms). So the goal is committed as `.task/goal.txt` in the post-install baseline, and every linked worktree allocated from the mirror carries the exact bytes. This mirrors the documented practice of committing owner inputs (`references/outer-loop.md`).
    - `.txt` keeps it outside the tasks' format checks.
    - It lies outside every allowed path, so a change to it is a scope violation.
  - **Roles file:** `--role-config` accepts the absolute, harness-owned `/harness/roles.json` in both arms.
  - `--max-rounds 4` is the shipped default. It is explicit, and frozen state must show it.
  - **The goal is 0222's product goal with its paths moved** (`0231/common.txt`). 0222's common text points to `/work/.devlyn/caller.json` and the repository at `/work`; it now says "Complete the development request in /harness/caller.json for this repository." Nothing else changes, including the local-only constraint, and the adapted bytes are frozen for both arms.
    - The caller contract stays because it carries `original_context`, the issue snapshot that 0222's product arms could read. Dropping the reference, as d3 proposed, would silently remove that task information.
    - `/harness/caller.json` is read-only and resolves from any worktree.

## Tasks and claims

D3 (`tj/commander.js`), D4 (`pallets/click`) and I0185 (`fysoul17/devlyn-cli`) keep 0222's registered bytes: sources, scope, public checks and oracle rows. D1 never runs.

- **D4 and I0185** are exposed to the design. 0225 derived the cuts from their F cost ledgers, and step 5's witness tags generalize their defect classes, although no task-specific clause entered the harness.
- **D3** is calibrated in 0222, and neither 0225's diagnosis nor the bundle design used it. It is still an exposed benchmark task.
- **Claims allowed:** a ship decision on these three exposed tasks. A completion gain on D4 or I0185 is descriptive only. Nothing here is holdout evidence.

## Cells and order

24 measured cells: 3 tasks × 2 configs × 2 arms × 2 replicates.
- Cells run serially, each in a fresh repository, home and session; nothing passes between replicates.
- Replicates reduce dependence on a single draw and reverse the arm order. They are not a significance test, and none is added after results are seen.

Each row below is two consecutive cells:

| Cells | Replicate | Task | Config | Order |
|---|---:|---|---|---|
| 1–2 | 1 | D4 | Claude | control → candidate |
| 3–4 | 1 | I0185 | Codex | candidate → control |
| 5–6 | 1 | D3 | Claude | candidate → control |
| 7–8 | 1 | D4 | Codex | candidate → control |
| 9–10 | 1 | I0185 | Claude | control → candidate |
| 11–12 | 1 | D3 | Codex | control → candidate |
| 13–14 | 2 | D3 | Codex | candidate → control |
| 15–16 | 2 | I0185 | Claude | candidate → control |
| 17–18 | 2 | D4 | Codex | control → candidate |
| 19–20 | 2 | D3 | Claude | control → candidate |
| 21–22 | 2 | I0185 | Codex | control → candidate |
| 23–24 | 2 | D4 | Claude | candidate → control |

Four SMOKE runs come first: the SMOKE task × 2 arms × 2 configs. They fall inside the approval scope and stay out of every sum and decision.

## Setup

- **Image v3** is 0222's pinned build (digest-pinned python base, Node 22.23.2, Claude Code 2.1.281, Codex 0.156.1, pytest 9.0.3) plus each task's declared check tools.
  - "Declared" means the dependency closure that the repository's own check scripts and type configuration name at its base commit. It is installed offline from that repository's lock:
    - D4: mypy 1.20.0 and pyright 1.1.408;
    - D3: commander's devDependencies (typescript, tsd, eslint and its plugins, prettier).
  - No environment managers (tox, uv). Public-check bytes are unchanged, and assessors run the same pinned CLIs inside the image.
  - **Placement.** The tools live in the image:
    - mypy comes from click's `uv.lock` hashes, and pyright from an npm lock at 1.1.408.
    - commander's devDependencies sit at `/node_modules`. That is an ancestor of every worktree path, so ESM imports and type roots resolve from any linked worktree without a `node_modules` in the evaluated source, and `tsc`, `tsd`, `eslint` and `prettier` are on PATH.
  - **Click's metadata only.** `/control/python` holds only Click's installed metadata, which its tests read. An installed copy of the code would silently replace the cell's own source whenever `src` was not first on the path.
  - **Path.** Participants run with `PYTHONPATH=src:/control/python`. Evaluators keep 0222's `/cell/work/src:/control/python` on the snapshot.
  - **Why:** in 0224, F-codex D4 ended on a missing type checker. The control still turns a missing tool into a product finding (0225 defect 3), while the candidate halts with `build-env-underprovisioned`. Unequal provisioning would decide the comparison instead of the bundle.
- **Cell layout.**
  - The anchor is `/cell/work` under a writable `/cell`, preserved at teardown. `/tmp` is a preserved bind mount too, because an owner may allocate its linked worktree there (shown by fixture). The root filesystem is read-only, and `CODEX_HOME/tmp` stays tmpfs (0224 Amendment 1).
  - **Origin:** `git@github.com:<repository>.git`, with the harness's `core.sshCommand` pointing at a sealed script.
    - The script serves `git-upload-pack` from a harness bare mirror whose `main` is the arm's post-install allocation SHA, and refuses every other command. The mirror holds no later refs, and the task's source SHA is recorded separately. D3 and D4 sources are shallow, so the mirror accepts a shallow update.
    - **Why:** allocation fetches its base from the remote, and the candidate's `task-complete.py` (`f71a17d3`) requires every remote URL to name one GitHub repository (`:152-166`) and fetches the base (`:388-392`). An unmodified cell would branch from today's upstream `main`.
    - **Model-free evidence so far:** with the bundle's real `task-complete.py allocate`, the baseline equals the registered base, `remote get-url` stays the GitHub URL, a push fails with rc 128, and the mirror is unchanged.
  - After allocation, the goal digest in state must equal the frozen goal and the frozen roles must resolve; this is shown by fixture.
  - `PYTHONPATH` never points at the anchor (`0222/prepare.py:116`).
- **Participant visibility:** the installer sees only the selected package, and runs see only public tools. Oracles, assessor inputs, the other arm's package and other cells are never visible.
- **Usage instrument:** `CODEX_ROLLOUT_TRACE_ROOT=/cell/trace` is set in every cell, for both arms (see Metrics). `/cell/trace` is participant-readable current-cell evidence, outside the evaluated source, and sealed externally after teardown. External sealing proves preservation after teardown, not immunity from earlier participant alteration; pre-seal trace evidence uses the existing evidence trust model.
- **Account:** both cells of a pair run on one account. Before the comparison and before each cell, a preflight checks auth, identity and the current limit state. No other research runs on that account during the comparison, and the account never switches automatically; a switch is a recorded venue change.

## Evaluated product

One snapshot is selected before grading:
1. an accepted commit validly bound to this task and run;
2. otherwise, the tree of the task-owned linked worktree at teardown (tracked and untracked, `.devlyn` excluded);
3. the anchor, only when no task tree was allocated.

- Every public check, oracle row and assessor consumes that one snapshot. Other teardown trees are kept as audit evidence, never as alternative products.
- Local-only completion returns before acceptance (candidate `task-complete.py:684-687`), so that is a normal path.
- A locator defect is an apparatus STOP. A participant's contradictory claim is product evidence.

## Metrics

- **Wall:** the owner's seconds from start to end. It includes nested workers, judges, repairs and the report, and excludes external evaluation. A hang counts as 5400 s. Phase intervals overlap and are never summed as savings.
- **OUTPUT:** provider output tokens over every model call the cell made: owner, native children, workers, probes, judges and repairs. Assessors, preparation, SMOKE and invalid runs are reported separately as research totals.
  - **Claude:** the owner's `modelUsage`, which includes native subagents (transcripts are a cross-check, never added), plus each separate `claude -p` result envelope, deduplicated by session.
  - **Codex:** per-inference `token_usage` from the traces, for every Codex thread in both arms. Rollouts are a cross-check where they exist.
  - The **trace contract** follows below. COMPLETE means reconciled native-reported usage, not provider billing.
- **Completion:** 0222's verdict on the selected snapshot.
  - COMPLETE needs every public check and oracle row to pass, clean scope, and both assessors calling it complete with no HIGH/CRITICAL.
  - NOT_TRIGGERED gives ADJUDICATE (0224 rule 1). Anything else is PRODUCT_INCOMPLETE.
- **Obligations** (binding for the candidate, reported for the control): VERIFY completed with a MECHANICAL seal equal to the final source, both judge carriers accepted (or a reported automatic pair skip), and FINAL_REPORT's verdict derived from that evidence with its render digest bound. The meter keys on obligations, never on phase names. A correct early halt that skipped the final review does not satisfy it.

### Trace contract

Probe evidence (2026-10-04, Codex 0.156.1, the judge flag set):
- With `--json`, stderr carries no model, effort, workdir or sandbox.
- In plain mode with the trace root set:
  - the native header stays intact, and `~/.codex/sessions` gains no file;
  - the trace's `manifest.json` names the header's session id;
  - `inference_started` names the model;
  - the single completed inference's response payload carries `token_usage`;
  - input − cached + output equals the printed `tokens used` (16,740 − 12,160 + 5 = 4,585).

Requirements:
1. **Inventory and binding.** Traces are reconciled against independently recorded launches (dispatch records, argv, transport carriers, worker receipts) and native child-spawn evidence, including failed launches.
   - Plain-mode roots bind to their header's session id, JSON roots to their native thread id, and native children by ancestry.
   - An unmatched call or an unexplained trace prevents COMPLETE.
2. **Counted once.**
   - Starts, responses and usage are bound by native identifiers. Archive copies are deduplicated, and distinct attempts are kept.
   - Whether a footer covers descendants is established, and rollout counters are compared after excluding inherited fork context (`0222/record_usage.py:33`).
   - Reasoning-output and cache-field semantics are validated on nonzero examples.
3. **Failed attempts.**
   - Known usage from retries, failed calls and inferences completed before a cancellation or timeout counts, and a successful retry does not erase earlier usage.
   - Missing terminal usage, a torn payload or unresolved compaction gives a named PARTIAL/UNKNOWN gap, never 0.
   - Collection runs through descendant teardown before sealing.
4. **Applicable cross-checks on every measured cell:**
   - Plain CLI roots (the judges): the manifest's `rollout_id` equals the header's session id, and Σ(input − cached + output) equals the footer's `tokens used`.
   - JSON roots (the Codex owner, workers): native thread identifiers and the existing identity evidence.
   - Native children: ancestry.
   - Trace sums equal rollout totals wherever a rollout exists.
   - Missing expected evidence prevents COMPLETE.
5. **Pins:** the CLI artifact and platform, the trace schema, the parser and the aggregation rules. Any CLI change voids the instrument.
6. **Storage:** trace volume is recorded and headroom checked before each cell. Truncation and disk failure are explicit, raw evidence is preserved before cleanup, and archive access is restricted until the audit ends. The trivial probe wrote 98,076 bytes, 90,906 of them one full request payload.
7. **Instrumented configuration:** wall results describe both arms with tracing on. Its overhead is not assumed to cancel.

## Decision rule

**Eligibility per (task, config)**, over its two replicates:
1. No candidate cell has a false completion or a scope violation.
2. The candidate's COMPLETE count is at least the control's.
3. For every public check and oracle row, the candidate's pass count is at least the control's.
4. No candidate tree has a reproduced HIGH/CRITICAL defect that the same concrete behavioral witness does not also reproduce in the control tree of its pair. Every assessor HIGH/CRITICAL gets a recorded reproduction.
5. Every candidate cell completed its obligations.

- An ineligible task blocks adoption in its config and is never dropped from the totals.
- **Owner decision and the recorded dissent.**
  - With b = control-only completions and c = candidate-only completions, rule 2 requires c ≥ b. The pairwise alternative, b = 0, differs only when b = c ≥ 1.
  - Root: replicates are exchangeable, so symmetric discordance carries no evidence of regression. The owner chose this rule.
  - Astra: symmetric discordance is zero observed net loss, not proven non-regression, and the adjacent pair should be the veto unit.
  - Per-pair results are reported beside the binding counts.

**Adoption in config k:** all of its eligibility holds, and over its 12 cells (6 per arm) either test passes:
- **Wall:** ΣW_candidate ≤ 0.85 × ΣW_control, and ΣO_candidate ≤ 1.10 × ΣO_control.
- **OUTPUT:** ΣO_candidate ≤ 0.75 × ΣO_control.

Rules for the sums:
- Candidate OUTPUT must be COMPLETE in every candidate cell, and the control is compared at its proven lower bound. An unproved inequality cannot establish its adoption test, but it does not veto the other test. If missing usage prevents establishing either test, the config is INCONCLUSIVE, which means not adopted.
- Sums over D4 and I0185 alone are reported, but never as a separate adoption path.
- An adoption in which both arms' products are incomplete is reported as such, not as productivity on successful work.

## Release

| Outcome | Effect |
|---|---|
| Adopted in both configs, final review and verification done | steps 2–5 become eligible for delivery into main |
| Rejected or INCONCLUSIVE in either config | the whole bundle stays held |
| A failure attributed to one step | no split release; a new registration is needed |
| Step 6 | not approved by this result |

Approving the comparison is not merge approval. Merging needs the owner's authorization, and npm publish stays with the owner.

## Faults

- **Carried over:** 0222's stops (a surviving container, a changed control manifest or sealed input, identity MISMATCH/UNVERIFIED, an evaluator that did not run, an assessor without a verdict). Also 0224 "Before any rule is computed" 1–3: ADJUDICATE, final-report audit, `.stop-N` rows, affected-bundle re-dispatch, and grading-only fixes regraded from preserved evidence.
- **Identity:** gaps feed the status, but a normal halt before any call is not an unverified model.
- **Quota** is classified from native limit evidence (error fields, transport records), never from a bare 429 or model prose.
  - Before dispatch: not dispatched, and the run waits.
  - During a cell: STOP. If only an assessor was affected, regrade from preserved evidence. If execution was affected, re-dispatch the affected bundle in its original relative order.
- **Apparatus faults:** a fault in the locator or the mirror is an apparatus STOP, never a product row. Lost usage evidence follows the trace contract's PARTIAL/UNKNOWN rules.
- **Never re-dispatched:** a verdict, or an incidental usage loss. That cell keeps its lower bound, which makes a candidate's OUTPUT INCONCLUSIVE.
- **Watchdogs only:** 90 min per owner, 10 min per review or assessor, 600 s per judge seat. There are no token, cost or call budgets.

## Apparatus acceptance (before FREEZE)

| Work | Evidence |
|---|---|
| Packing and 4.x install | Both arms install offline in both configs; source → package → installed bytes link up; skills are discovered; the baseline is clean; fixtures refuse a wrong arm and 0222's old routes. |
| Image and tools | Binary, version and digest inventory. The registered project checks run offline against the linked task source, and a mutation planted only there is caught by runtime import and the type checkers. Provisioned dependency files stay outside the evaluated source. |
| Participant boundary | The participant cannot read or list oracles, other tasks, the other arm's package or other cells, and public tools work. |
| Mirror and allocation | Both arms allocate from the post-install SHA, and goal and roles stay usable. The script and mirror manifest are sealed; upload-pack requests naming another repository and all other commands are refused. |
| Snapshot locator | Success, NEEDS_WORK, BLOCKED, local-only and cleanup paths each select one snapshot, and the other trees are preserved. |
| Identity | Run, round, role, resolution, prompt, argv, transport and native model link up. Fixtures reject a seat swap, a wrong model or effort, a stale round, another cell's evidence and a missing failed call. |
| Usage | The trace contract's fixtures: children, duplicates, retries, interruption, compaction and missing evidence, each with an exact total or a named gap. |
| Obligation meter | The candidate's normal evidence passes, shown on real archives its own scripts build. The control's 4.1.0 evidence is reported descriptively, because rule 5 binds the candidate only and the control's records have a different shape. A missing gate or judge, an empty or unbound carrier, a source change after review, or a stale terminal is rejected. The meter runs only the arm's frozen helpers from the control tree. |
| Decision calculator | Boundaries at 0.85, 1.10 and 0.75; configs computed separately; replicate keys distinct; ineligible cells kept. Missing candidate OUTPUT gives INCONCLUSIVE, and partial control OUTPUT uses its proven lower bound. Fixtures: complete totals W 80/100 with O 105/100 pass the Wall test; complete candidate O 60 against a partial control's proven lower bound 100 passes the OUTPUT test. |
| Faults | Quota, auth, teardown, identity and evaluator failures; regrade vs re-dispatch; STOP files never skipped as success. |
| Calibration | The evaluator in image v3 reproduces 0222's 23/23, and the container tests run rather than skip. |

**SMOKE**, which runs first after approval, must show:
- the registered routes;
- allocation from the mirror;
- snapshot selection;
- routed identities;
- both arms' usage reconciled COMPLETE under the trace contract;
- clean teardown.

A failed SMOKE blocks measurement. If SMOKE requires a product change, the candidate is re-frozen and its earlier SMOKE evidence lapses.

## Predictions (before any run)

**Astra** (R0 §10):
1. Measured cells have no identity error, required-tool infrastructure halt or shared quota STOP.
2. All 12 candidate cells complete their obligations.
3. The candidate loses no public check or oracle row and adds no reproduced HIGH/CRITICAL.
4. Wall ratio: claude in [0.65, 0.85], codex in [0.70, 0.90].
5. OUTPUT ratio: both configs in [0.55, 0.75].
6. On D3 and D4, the candidate completes at least one of its two replicates in each config.
7. On I0185, the control completes 0 of 4 and the candidate at least 1 of 4.
8. Both configs are adopted.

**Root** (restated after convergence; R0's figures assumed `--max-rounds 2` and a lower-bound control):
1. Every cell gets a verdict, with at most one infra stop (an account limit).
2. Wall ratio: claude ≤ 0.80, codex ≤ 0.90.
3. OUTPUT ratio: claude ≤ 0.70, codex ≤ 0.80.
4. Candidate usage is COMPLETE in all 12 candidate cells.
5. I0185 is incomplete in all 8 of its cells. D3 and D4 each complete in at least half the cells of each arm.
6. Adopted in claude; codex is a coin flip. P(adopted in both) ≈ 0.45.

A ratio is the candidate's 6-cell sum over the control's, per config. Without COMPLETE usage, an OUTPUT prediction is reported as unverifiable, not as held.

## Order to the run

1. This draft goes to Astra review.
2. Root implements the apparatus with its model-free evidence, and Astra verifies it.
3. A Claude multi-lens review covers the bundle rounds after `f1c06224` and any later product change. A product fix re-freezes the candidate.
4. Astra FREEZE of the registration: SHAs, packages, image, CLI artifacts, apparatus, roles, dispatch and rules. Any later change is an addendum.
5. The owner approves the 4 SMOKE and 24 measured resolve runs.

## Honest limits

- The tasks are exposed and n is small. Replicates are not a significance test.
- Results hold for the instrumented configuration, the pinned CLI pair and the image's tool set.
- Claude judges' effective effort is unverified.
- The trace instrument is an undocumented CLI interface, pinned and cross-checked, and it voids on any CLI change.
- The seal's trusted-environment boundary (owner decisions R1, R2) is unchanged.
- This comparison does not test live witness recall, Claude worker prompt-delivery attestation, or polling elimination.
