# 0230 — develop the held 0225 bundle: steps 3–5 on the ported candidate

2026-10-03. **Status: DESIGN CONVERGED (Astra R1).** Development only. Nothing ships, and no resolve run happens under this record.

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

PR #159 (`candidate/bundle-step3`, commits 363c11b1 + 0a522619): 61 files, both skill trees, net ≈ −2,900 lines per tree. Lint, test-windows-portability (72 OK), every `_shared` self-test and the rewritten test-owner-phases pass; CI POSIX and Windows.

**Review.** Astra ultra v1 REVISE (5) → v2 REVISE (4) → v3 REVISE (4) → v4 SHIP. A five-lens Claude review with two refuters per finding confirmed 10 findings (6 distinct), all fixed. New guards were mutation-checked: each fixture fails with its guard removed.

**Refinements of the converged design, with the named delta for each:**
- **Scope runs on the snapshot tree before any command** (not after cleanup). Delta: Astra v1 showed a literal's run artifact produced a CRITICAL scope finding that persisted after cleanup removed it. The sealed tree must equal the snapshot, so the scope-checked tree is the final tree.
- **The snapshot is retaken once after staging, before the first command**, by the process that claimed it (O_EXCL + owner nonce). Delta: Astra v2 showed the staged `spec-verify.json` is authoritative in benchmark mode. Staging rewrites it after the opening snapshot.
- **Normal mode counts a PHASE 0 baseline entry by path and kind, not bytes. A nested repo or worktree (`?? dir/`) counts by path.** Delta: the Claude review reproduced two failures. A user's nested repo crashed the snapshot. A check that rewrites a pre-existing untracked cache made every round unsealable, and the owner may not touch baseline files. Verify-only still hashes every byte, nested trees included.
- **Only the dispatch record binds the seal file, so it is current-round only.** Delta: `source-seal.json` is not round-scoped.
- **G2 (binding language/browser gates) is lint-pinned, with no gate inventory script.** Astra accepted this delta: BUILD_GATE never had a mechanical inventory either.

**Pre-existing, unchanged:** with no verification contract at all, the main run returns before its commands. The seal and the finish gate still catch untracked and tracked leaks.

**Follow-up for the live-comparison registration:** benchmark/ceiling scripts key on `phases.build_gate`/`cleanup` for historical cohorts. Comparison meters must key on obligations (0225:137).
