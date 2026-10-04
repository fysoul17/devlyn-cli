# 0230 — develop the held 0225 bundle: steps 3–5 on the ported candidate

2026-10-03/04. **Status: PR-3, PR-4 and PR-5 are merged into the bundle, and so are the whole-bundle review fixes (PR #164, `f71a17d3`). Next is the live-comparison registration.** Development only. Nothing ships, and no resolve run happens under this record.

**Owner direction (2026-10-03):** "묶음 개발 재개해 줘. astra ultra 와 나중에 검수/검증까지 확실하게" — after [0229](0229-verify-existing-behavior-rescreen.md) PASS readmitted 22616b57 + F + G + H, prepare 0225 steps 3–5, with a thorough Astra ultra review at the end. Per [0226](0226-verify-recall-screen.md):83, a live comparison of the bundle needs its own registration and the owner's approval to run resolve. Per [0225](0225-resolve-cost-cuts.md) "Release", steps 2–5 ship only as a bundle adopted in both configs.

## Where the bundle stands

- **Branch:** `bundle/0225-steps-2-5` on origin. Step PRs target it, never main.
- **Port (PR #157, merged as `1c23ba86`):** the 0229 candidate's product diff against step 1, replayed onto main 4.1.0 (skills renamed to `devlyn-<x>`, 4.0.1 skill-dir binding, AGENTS-first install). Astra SHIP (51 paths accounted for, 24 mirror pairs equal); two Claude reviewers found no port defect; CI POSIX and Windows pass.
- **Step-2 follow-up (`candidate/bundle-step2-fix`):** the compat reviewer found three gaps in the candidate itself, reproduced by root and confirmed by Astra (`.devlyn/bundle/step2fix-r0-astra.out.md`):
  1. an omp orchestrator, `--engine omp` or an omp executor pin stopped at role freeze (`judge-route-unsupported:omp`);
  2. a grok-only `pair_judge_priority` reported `grok-unavailable` instead of `judge-route-unsupported:grok`;
  3. `--global --claude` never sets the Bash ceiling VERIFY's foreground call needs.

  **Owner decisions (2026-10-03):** item 1 = automatic assignment (an inherited primary judge on an engine without a scripted judge route goes to the first available of claude, codex, recorded in its source; explicit judge roles stay fail-closed). Item 3 = guidance only (global installs never edit user settings). Item 2 is an engineering fix.

## Design process

Inputs: the four maps in `.devlyn/bundle/maps/` (gate, owner, plan, tests) and `.devlyn/bundle/design-brief.md`.

- **Astra R0:** an independent design (`design-r0-astra.out.md`).
- **Claude:** two designs per step (maximum deletion, guarantee first), an adversarial critic per step and a cross-step integrator (`design-claude-{step3,step4,step5,plan}.md`).
- **Astra R1** (`design-r1-astra.out.md`) adjudicated the 11 differences.
  - Astra adopted Claude's gate placement. Named delta: the VERIFY validator authenticates a VERIFY carrier (`verify-merge-findings.py:184`), and 0225:137 makes obligations, not phase order, decisive.
  - Astra retracted its R0 proposal to attach witnesses to I0185/D4 clauses (comparison independence).
  - Claude's design takes Astra's amendments below.

## Owner decisions on product behavior (2026-10-03)

| # | Decision | Effect |
|---|---|---|
| U1 | Mechanical exhaustion ends `NEEDS_WORK` | A product check that still fails after the repair budget is a product failure, not infrastructure. Infra failures stay `BLOCKED`. |
| U2 | Delete `--bypass build-gate,cleanup` | Bootstrap's existing unknown-flag rule returns `BLOCKED:invalid-flags`; docs drop it. |
| U3 | The required-tool halt is `BLOCKED:build-env-underprovisioned` with operation `tool` | Reuses the sealed capability-denial floor, keeping SKILL.md:303's proof; no separate `required-tools-unavailable` token. |
| U4 | Run risk probes more often | Delete the small-surface demotion. A validated, nonempty `required_risk_probe_requirements` declaration sets `high_risk`. Explicit opt-out and visible skip when the OTHER engine is unavailable stay. |

## Converged design

### PR-3: one final mechanical gate

**Phases:** PLAN → RISK_PROBES? → IMPLEMENT → VERIFY{MECHANICAL → judges → merge} → FINAL_REPORT. BUILD_GATE, CLEANUP and SURFACE_CLOSE leave the phase graph; `cleanup.md` and `surface-close.md` are deleted, and `build-gate.md` becomes `mechanical.md`.

**MECHANICAL steps** (the same entry point in normal and verify-only modes):
1. Seal snapshot S0.
2. `spec-verify-check.py` runs literals, probes and expected-contract checks once.
3. The owner runs the binding language gates and the browser tier.
4. The owner removes proven run-owned artifacts.
5. Snapshot S1 must equal S0. The scope check runs, then the seal is recorded.
6. `verify-judges.py`.

**Seal** (composed, cheap):
- **Binds:** HEAD; tracked and index cleanliness outside `.devlyn/`; the untracked baseline file's bytes (equality, not just "no additions"); untracked paths, types, modes and bytes (a symlink by link text); and explicit verification inputs, including the sibling expected file's bytes, which today have no digest (`phase-prompt-render.py:75`).
- **Reuses:** the existing contract, PLAN and probe digests, revalidated rather than duplicated. Command and timeout evidence stays in its current carrier.
- **Rechecked at:** all three mechanical consumers (`verify-judges.py:218`, `verify-merge-findings.py:352,529`) and at final acceptance (`task-complete.py`). A mismatch invalidates the evidence; it is never refreshed over old results.
- **Verify-only:** keeps its PLAN exemption, but its reviewed inputs are sealed too.
- **Refusal:** one HIGH `scope.unsealed-source` finding naming the paths. It keeps today's repairable CLEANUP-FAIL route (`state-phase-write.py:2024,2030`).

**Repairs.** Origins shrink to `implement` and `verify` (`REPAIR_PHASES` shrinks, not deleted). The minimal checkpoint checks stay: triggering-findings digest, round and origin, clean tree and index, fix parent and subject, receipt hash. The surface-restoration machinery is deleted. The writer records `verify.pre_sha` itself; `--pre-sha`, `--post-sha`, `--input-patch-sha256`, `--untracked-before-json` and their `--next-*` twins are deleted.

**Required tool (U3).** `tool` joins process-evidence capabilities. The owner records a denial with the S:303 proof; the existing floor (`process-evidence.py:544`) gives VERIFY BLOCKED, skips judges and admits no repair.

**Terminal classifier.** Close the hole Astra reproduced: `terminal-claim-check.py:116` accepts any `*-unavailable` reason after an IMPLEMENT PASS. Restrict it to supported engine routes with their witnesses.

**Also in PR-3:**
- Declared process-evidence obligations that name `build_gate` (`process-evidence.py:98`) move to `verify` with identity and provenance preserved.
- Historical archives keep their readers; only new runs lose the phases. Old origins are not reclassified INCOMPLETE.
- `task-complete.py` success requires PLAN, IMPLEMENT, VERIFY with a valid seal equal to the accepted source, the finish-gate summary, and report and archive bindings.
- `finish-gate.py` loses its cleanup window. Revert-and-unclean stays.
- Lint runs the finish-gate, resolve-bootstrap and terminal-claim-check self-tests. The mirror list gains `finish-gate.py` and `mechanical.md` and loses the three deleted files.
- The `verify-merge-findings.py:782` surface-close prerequisite is deleted.
- Doc upkeep (CL:14-16, SC:16 UVR-STALE) moves into `implement.md`.

**Negative fixtures:** every moved guarantee, including the following. Each rejection also asserts byte-identical state.
- Seal: one per sealed input changed independently, before and after dispatch; stale run or round; an S0≠S1 residue.
- Required tool: end to end, giving VERIFY BLOCKED, no admission and an unchanged round counter, then an archived run TCC CLEAN. An unsupported `*-unavailable` claim is rejected.
- Exhaustion: exhaustion → report → archive → TCC on the VERIFY origin.
- Historical-archive readability.
- `--bypass` → `invalid-flags`.
- Finish-gate offender exits 2 after a successful revert.

### PR-4: fewer owner turns

**Scripted owner edits:**
- Bootstrap records `--risk-probes` and `--no-risk-probes`; freeze takes `--complexity` and `--high-risk-reason` and binds `criteria_sha256`.
- The probe_derive PASS validates probes through the full CLI path and binds `risk_probes_digest` under the lock. This deletes the unlocked heredoc.
- `exec` is derived from the bound plan only with ≥2 `### Phase` blocks. IMPLEMENT PASS advances it uncharged.
- `criteria[]` and the checkbox ticks are deleted.

**Verdict and report.**
- `--phase final_report complete` derives every verdict and reason available from validated evidence and refuses contradictions, such as a BLOCKED reason that disagrees with a recorded denial.
- A supplied halt reason is accepted only where state cannot provide it.
- One renderer writes the report, and the final message relays it byte for byte. The existing marker, digest, archive and delivery bindings stay.

**Instructions.**
- Exact command recipes per edge. No API-discovery reads; `task-completion.md` is read only when this session has not allocated.
- Probe text loads only when probes are enabled, explicit or automatic (`references/risk-probes.md`).
- The `process-evidence.py` denial refresh becomes a CLI (deleting the runpy recipe).

**Demotion.** The small-surface demotion stays as written until PR-5 deletes it.

**Codex polling (honest limit).**
- PR-4 ships: foreground invocation, timeout and cancellation recipes, no status or heartbeat reads, and maximum-wait resumes.
- It does **not** claim polling elimination. A delayed-child host test proving no owner continuation before completion stays open.

**Static checks:** bootstrap/state parity (including `session_id`, `engine_source`, `role_config_input` in the schema), the report/verdict agreement matrix, archive integrity and conditional loading.

### PR-5: contract-first PLAN

**PLAN without restatements.** `plan.md` keeps the surface sentinel, risks the contract leaves open, and conditional execution phases with `gate:` lines (no checkboxes). The acceptance restatement and the other copies are deleted (`plan.md:6,20,31`, `implement.md:10`, `SKILL.md:134`).

**Renderer worker mode.**
- The renderer frames the canonical contract and goal bytes (hash-checked, newline-exact), the metadata (run, phase, round, path bindings from its own location, `exec` when present), the requirements (probe_derive) and the findings (IMPLEMENT, read from state).
- The owner writes no prompt text.
- Order: complete → render → spawn, requiring a completed, bound PLAN. `--next-prompt-sha256` is deleted after its callers.

**Probes (U4).**
- Delete the small-surface demotion.
- Allow inline `required_risk_probe_requirements`; staging rejects them today (`spec-verify-check.py:688`) while enforcement reads them (`:855-862`).
- A validated declaration sets `high_risk`.

**Defect-4 witnesses.**
- Four generic tags with marker contracts: release recovery, physical alias, fixture cleanup, temporary-file preservation.
- One synthetic defective/fixed fixture repository, run through staging → probes → process evidence → findings. The defective build fails each probe; the fixed build passes.
- **Nothing task-specific enters the harness:** no I0185/D4 clauses, identifiers, routing, fixtures or oracle paths.

**Static checks:** source identity, immutable scope and gate preservation.

## Process per PR

1. Root implements on a branch from the bundle head.
2. Mirror `.agents/skills`, then run lint, portability and every self-test.
3. Astra ultra verifies until SHIP, then gh PR into the bundle branch, CI, merge.
4. After PR-5: a whole-bundle multi-agent review plus an Astra ultra verification, then a live-comparison registration that waits for the owner's approval to run resolve.

The comparison meters key on obligations, not phase names (0225:137). `experiments/0225/replay.py:74` reads `phases.build_gate`.

## PR-3 result (2026-10-03)

PR #159 (`candidate/bundle-step3`, commits 363c11b1 + 0a522619): 64 paths; each skill tree +1,682 / −4,220 (net −2,538). Lint, test-windows-portability (72 OK), every `_shared` self-test and the rewritten test-owner-phases pass; CI POSIX and Windows.

**Review.** Astra ultra v1 REVISE (5) → v2 REVISE (4) → v3 REVISE (4) → v4 SHIP. A five-lens Claude review with two refuters per finding confirmed 10 findings (6 distinct), all fixed. Mutation checks run: Astra's 18 G2 lint-deletion mutations, and root's removal of each new seal guard (comparison, `--ignore-submodules=none`, staged carrier, nested-tree digest, traversal onerror, linked-directory hashing, snapshot owner check); every one fails its fixture.

**Refinements of the converged design, with the named delta for each:**
- **Scope runs on the snapshot tree before any command** (not after cleanup). Delta: Astra v1 showed a literal's run artifact produced a CRITICAL scope finding that persisted after cleanup removed it. The sealed tree must equal the snapshot, so the scope-checked tree is the final tree.
- **The snapshot is retaken once after staging, before the first command**, by the process that claimed it (O_EXCL + owner nonce). Delta: Astra v2 showed the staged `spec-verify.json` is authoritative in benchmark mode. Staging rewrites it after the opening snapshot.
- **Normal mode counts a PHASE 0 baseline entry by path and kind, not bytes. A nested repo or worktree (`?? dir/`) counts by path.** Delta: the Claude review reproduced two failures. A user's nested repo crashed the snapshot. A check that rewrites a pre-existing untracked cache made every round unsealable, and the owner may not touch baseline files. Verify-only still hashes every covered untracked byte, including nested-tree contents (ignored paths and nested `.git` directories excepted).
- **Dispatch binds the seal for merge; current VERIFY state binds it for archive and acceptance. Its binding is excluded from history** because the filename is reused each round.
- **G2 (binding language/browser gates) is lint-pinned, with no gate inventory script.** Astra accepted this delta: BUILD_GATE never had a mechanical inventory either.

**Pre-existing, unchanged:** with no verification contract at all, the main run returns before its commands. The seal and the finish gate still catch untracked and tracked leaks.

**Follow-up for the live-comparison registration:** benchmark/ceiling scripts key on `phases.build_gate`/`cleanup` for historical cohorts. Comparison meters must key on obligations (0225:137).

## PR-4 result (2026-10-03)

PR #161 (`candidate/bundle-step4`, commits e6434e3d + a787b1c0 + 99bab57e), merged into the bundle as `ea14d7fe`. Each skill tree changes +1,037 / −404:
- **Scripts (`_shared`):** +896 / −246. Of that, the self-tests are +474 / −191 and product code is +422 / −55.
- **Docs (`devlyn-resolve`):** +141 / −158.

Lint, test-owner-phases, test-windows-portability and the touched self-tests pass at 99bab57e (root runs, reported in the v3 prompt). PR #161 CI passes on POSIX and Windows (Actions run 37112152416).

**What the scripts now own.**
- **Bootstrap:** records the `--risk-probes`, `--no-risk-probes` and `--no-pair` fields.
- **Freeze:** binds complexity, criteria bytes, high-risk reasons and the automatic-probe decision. Verify-only never auto-enables probes, because MECHANICAL would then require a probe file that verify-only can never produce.
- **Probe derive:** a PASS binds the probe digest.
- **Phase-gated progress:** the writer counts `### Phase <k>` headings within `## Execution phases`, excluding fenced content.
- **Final report:** `final_report complete` derives the verdict from recorded state and evidence, requires a supplied `BLOCKED:<reason>` when it cannot derive the halt reason, and renders the report.
- **Denial CLI:** refreshes the results carrier.

**Kept as owner prose until PR-5:** the small-surface demotion. It is the one locked owner edit left.

**Review.**
- **Astra ultra:** R0 REVISE (8), v1 REVISE (5), v2 REVISE (3), v3 SHIP.
- **Five-lens Claude review** (workflow `wf_2dfb3815-3bf`; the script gave each finding two refuters): 27 confirmed findings, about 15 distinct. The v2 prompt lists the fixes, and Astra v2/v3 found no incorrect fix beyond the three v2 findings, which v3 closed.
- **Regression it caught:** halts before IMPLEMENT got `finish-gate-unclean`, because the real finish gate is malformed without a usable PLAN surface. That made TCC's plan-empty witness unreachable. Now exit 2 always decides, while exit 1 decides only once IMPLEMENT has started. The finish gate also keeps its first result, so a rerun after automatic reverts cannot launder a clean pass.
- **Mutation checks:** root's guard-removal run killed all 36 listed mutations (v2 prompt), and 4 more for the v2 fixes (three fence conditions, the changed-criteria order). This is a listed set, not an exhaustive inventory of every guard.

**Honest limits.**
- The Codex foreground, timeout and maximum-wait recipe is a mitigation; a delayed-child host test is still open.
- Product code grew by about 370 lines. In return, the moved state writes and the report rendering became script-enforced. The small-surface demotion remains an owner edit, and halts without a derivable reason still need a supplied reason. Per skill tree, `SKILL.md` shrank by 78 lines; the resolve docs overall shrank by 17.

## PR-5 result (2026-10-03)

PR #163 (`candidate/bundle-step5`, commits de8c4350 + 2c1f50d9 + 31d12e0f + b90cbe7e), merged into the bundle as `ac90bb0c`. Each skill tree changes +821 / −194:
- **Scripts (`_shared`):** +746 / −145, most of it the renderer worker mode, its tests, and the witness fixture.
- **Docs (resolve and ideate):** +75 / −49.
- **Test scripts:** +162 / −1.

Lint, test-owner-phases (15), test-windows-portability and every touched self-test pass. PR #163 CI passes on POSIX and Windows (Actions run 37119409361).

**What changed.**
- **Rendered worker prompts.** `phase-prompt-render.py --devlyn-dir .devlyn --phase implement|probe_derive --engine E --round N` builds each prompt from completed state. The prompt carries:
  - the projected adapter and the canonical body;
  - the exact contract and goal bytes, hash-checked;
  - path bindings taken from the renderer's own location;
  - the phase-gated `exec` and `repair_of`;
  - the merged findings on a VERIFY repair, or the declared requirements for probe_derive.

  The owner writes no prompt text. Every edge into PROBE_DERIVE or IMPLEMENT runs complete → render → spawn. The PLAN-PASS `complete` refusal and `transition --next-prompt-sha256` are deleted.
- **Renderer refusals** (`BLOCKED:phase-input-invalid:<kind>`) leave the output untouched. They close through FINAL_REPORT with the bare label, which TCC accepts as a halt witness at the last reached phase. FINAL_REPORT records a PLAN that no longer verifies instead of refusing. Findings and criteria in the report are display-only. The finish gate verifies the bound PLAN before it interprets the surface or reverts anything.
- **Contract-first PLAN.** plan.md, implement.md, probe-derive.md, risk-probes.md and SKILL no longer carry the acceptance restatement or owner-pasted context. implement.md now gives the worker canonical instructions: path bindings, the worktree, probes, `exec`, and the scope of each repair.
- **U4 (probe policy).**
  - The small-surface demotion is deleted.
  - Inline `required_risk_probe_requirements` are accepted. The resolver and staging share one shape rule and a cap of three distinct bullets, since a run derives at most three probes.
  - The freeze marks declared requirements as high risk (reason `declared-risk-probe-requirements`) under the existing gating.
- **Defect-4 witnesses.** Four generic tags with marker contracts: `release_recovery`, `physical_alias`, `fixture_cleanup` and `temp_file_preservation`. `defect_witness_self_test` runs one synthetic store CLI with four independently switchable defects through MECHANICAL, using three probes:
  - the fixed build passes and seals;
  - each single defect fails exactly its own probe (P1 names which sub-check failed);
  - it also runs natively on Windows CI.

  Nothing task-specific entered the harness.

**Review.**
- **Astra ultra:** R0 REVISE (9; all adopted), v1 REVISE (2), v2 REVISE (3), v3 SHIP.
- **Five-lens Claude review** (workflow `wf_94d1d502-874`, two refuters per finding): 10 confirmed, 6 distinct, all fixed.
- **Mutation checks:** root's listed guard-removal mutations (22 + 6 + 3) were all killed.
- **CI:** the first run failed on Windows. The renderer's existing VERIFY self-test, which runs natively there for the first time in this PR, wrote a hashed fixture in text mode (CRLF). b90cbe7e writes exact bytes.

**Honest limits.**
- The live recall of the witness tags still depends on the probe engine. The fixture proves the mechanism, not recall.
- Claude/omp delivery of the rendered bytes is not attested (step-6 territory).
- A permanent VERIFY snapshot digest pin was not added, because the fixture's git SHAs change on every run.

## Whole-bundle review (2026-10-03/04)

The review covered bundle head `ac90bb0c` and found:
- Astra ultra: REVISE (5) (`.devlyn/bundle/bundle-review-astra.out.md`);
- a six-lens Claude review: 15 confirmed.

The fixes are PR #164 (`candidate/bundle-review-fix`), merged into the bundle as `f71a17d3`. That is nine commits, `cfc405f6` through `9679381f`, with `config/skills` at +1357 / −352. CI passes on POSIX and Windows.

**Process.**
- **Fix v1** (`cfc405f6`): Astra REVISE (2). A seven-lens Claude review with three refuters per finding confirmed 38, about 25 distinct.
- **Design rounds 1–4 with Astra.** The owner asked whether the planned fixes were best practice and to settle them with Astra (`.devlyn/bundle/bundle-fix-v2-design-*`, converged record `bundle-fix-v2-design-converged.md`). Both sides reversed a position, each with a named delta:
  - Astra dropped presence-refusal of index flags after six confirmed sparse-checkout and ignoreStat regressions.
  - Root dropped "count only tracked-rule ignores as environment", because `gitignore(5)` puts editor and per-user patterns in local and global excludes.
- **Fix v2** (`a0e4994b`, `f1c06224`): Astra REVISE (4). A second seven-lens Claude review confirmed 44 of 49. Each one was fixed, made moot by an owner decision, or deferred with Astra's acceptance.
- **Fix v3–v6** (`3cf16ba8`, `06dca174`, `fe4b9130`, `23842dc3`, `484e627c`, `9679381f`): Astra REVISE (3), then REVISE (1), REVISE (1), and v6 **SHIP** with no new findings across `f33cf2ca..9679381f`.

**Owner decisions (2026-10-04).**

| # | Decision | Effect |
|---|---|---|
| R1 | Git conversion filters (#30) are documented as trusted environment, not closed | The seal claim is qualified. Astra recommended closing; root recommended documenting. |
| R2 | Ignore rules of every source, including rules added during a run, and the content they hide are trusted environment | The ignore-rule identity (`base_ref.excludes_sha256`) is deleted. Claude Code itself appends to the global and local exclude files, and pytest and venv write self-ignoring cache `.gitignore` files, so the binding refused correct runs. |
| R3 | A completed BLOCKED work phase witnesses a dependency `<x>-unavailable` reason | TCC now matches the writer. Absent-worker handoffs stay narrow. |
| R4 | An untracked file that predates the run is adopted only by an exact `authorized_surface` entry | A glob never stages or commits a user's file, and a nested repository counts in both spellings, `dir/` and `dir`. |

**What changed.**
- **Halt reasons.**
  - `role-config.py` owns its refusal vocabulary, and engine names follow the reason grammar.
  - The writer's `halt_reason()` decides PHASE 0 closes, and TCC witnesses with the same predicate.
  - Reasons are canonical labels; prose goes to `--detail`.
  - A halt witness needs a completed final report.
  - `untracked-baseline-unwritable` closes a failed step-2 baseline write.
- **VERIFY admission** requires a finished IMPLEMENT: PASS or PASS_WITH_ISSUES, with every execution phase passed.
- **Seal observation.**
  - `observed_git` works on a private index copy (mtime kept). It clears assume-unchanged and skip-worktree, except on the baseline's authorized sparse absences, and turns off fsmonitor, the untracked cache, ignoreStat, split index and hooks.
  - These consumers all use it: bootstrap cleanliness, scope, staging, the snapshot, the finish gate and the expected-contract readers.
  - `untracked.baseline` is typed JSON (`untracked`, `sparse_absences`).
  - The blanket index-flag refusal is deleted, so sparse checkouts seal.
- **Finish gate.**
  - A PHASE 0 halt has an empty surface.
  - Paths at base are restored. Other offenders keep their bytes and lose only their index entry.
  - Pathspecs are literal.
  - A drifted sibling contract is settled by its binding.
  - Submodule pointers are enumerated.
- **Delivery.** The sibling contract must equal the accepted commit. A pre-seal archive is refused with guidance; an already-bound delivery resumes.
- **Probes.** Automatic probes skip, and explicit `--risk-probes` is refused at bootstrap, for a spec without a verification section.
- **Repair checkpoint.**
  - Base paths are restored. Other offenders lose only their index entry, and only the repair deletes a file it created.
  - The fix commit may be empty.
  - Commands use `git --literal-pathspecs`.
- **Cleanups.**
  - stale docs, including README's seal claim;
  - the benchmark oracle's retired edge;
  - duplicate helpers and an unreachable generated-carrier branch (the freeze owns that refusal);
  - an orphan parameter.

**Verification.**
- Every round: lint-skills, `git diff --check`, test-owner-phases (22 at the end), test-windows-portability, plan-dispatch-oracle and every touched `--self-test`.
- 38 guard-removal mutations were killed across the rounds: 6, 12, 4, 11, 3, 1, 1.

**Honest limits.**
- **Claude review coverage.** No Claude multi-lens review covered the rounds after `f1c06224`. The Claude weekly usage limit (resets 2026-10-10 08:00 KST) stopped the second review's gap pass. Its two unverified gap findings: one doc fix adopted, one pre-bundle follow-up.
- **Deferred, now failing closed and visibly.** Staging paths that carry index flags (plain `git add` skips assume-unchanged entries and refuses skip-worktree ones), additions outside a sparse cone, and implement-empty ignoring untracked or staged changes.
- **Pre-bundle follow-ups.** Risk probes import unattested modules from `.devlyn/probes/`; `pipeline.state.json` is worker-writable (#35); `process_evidence` is missing from the contract validator (#36/#38).
- **A narrower seal.** The seal guarantees less than the bundle first claimed. `phases/mechanical.md` step 5 lists the trusted environment.

