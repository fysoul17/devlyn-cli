# Work packet I1-resolve-responsibility-map

Generated 2026-09-24 against main @466aa25 by a read-only scoping agent, then checked by an adversarial verifier (verdict: **READY_WITH_FIXES**). **Verifier corrections below override the packet body where they conflict.** Line numbers drift: re-check every location against the session's base SHA before editing. Registration: [0221](../../../iterations/0221-subtraction-direction.md).

**Used in:** Session 5 (build /devlyn:intent from the KEEP/MOVE rows; add, do not delete). Session 9 (delete helpers whose references are gone). Do not delete resolve or shared helpers in Session 5.

## Summary

This packet maps every phase, rule, state field and flag of /devlyn:resolve (config/skills/devlyn:resolve/SKILL.md 369 lines, 55,701 bytes; 12 files total, 1,587 lines, 161,135 bytes) to a 4-responsibility kernel. The kernel becomes a new /devlyn:intent entry built on autoresearch/experiments/0204/owner.md, an owner prompt that was traced in 0204 and 0205. Mapping: (1) the user contract comes first (immutable source bytes, authorized scope bound before the first edit, explicit routes fail closed); (2) one native owner plans, implements or delegates to the pinned executor, and runs real checks; (3) counterexamples are reproduced, repaired and rechecked, with a fresh independent review (dual-engine when the OTHER engine is available, per NORTH-STAR.md:269); (4) one deterministic verdict writer that works from sealed evidence, so failure or missing evidence never becomes PASS. SURFACE_CLOSE, RISK_PROBES, the complexity/risk classifier, phase-gated IMPLEMENT, the CLEANUP/BUILD/PLAN phase lifecycle, FINISH_GATE, final-report binding, the Stop hook, pair_trigger telemetry and solo-headroom vocabulary are deleted or moved into the owner. Deletion evidence: 0075 rollback discarded correct repairs; 0113 smoke-1/3 SURFACE_CLOSE blocks; 0196 CLEANUP 14/14 no-op trees; 0099 dead reread; 0074.3 Stop hook is pressure, not authority. In _shared, 4 files are deleted and state-phase-write.py and 9 other files are shrunk. Estimated result: the intent skill is about 430–470 lines (~35–40 KB, −72% lines / −75% bytes), and _shared goes from 25,987 to ~16,500 lines (−36%). The PR also migrates installs: it purges devlyn:resolve and the exact legacy Stop-hook entry, and changes the delivery default to push+PR with no auto-merge.

## Items

### 0. DECISION RECORD A — DELETE (no kernel responsibility; evidence of cost/harm). Input to the Astra design round; nothing here is executed on its own.

**Change.** DECISION RECORD A — DELETE (no kernel responsibility; evidence of cost/harm). Input to the Astra design round; nothing here is executed on its own.

**Files / lines.** D1 SURFACE_CLOSE: SKILL.md:270-274, :23 (halt list), :71, :357, :359; references/phases/surface-close.md:1-34; state-schema.md:65; state-phase-write.py surface*/rollback/adjudication/parse_effective_model (~lines 470-1290, 937-975); archive_run.py pattern "surface-close.output.json"; lint 579-656. Evidence: autoresearch/iterations/0075-residual-decomposition-pc-formal.md:145-157 (format-rejection rollback discarded the worker's CORRECT repairs; 3rd occurrence of the class); autoresearch/iterations/0113-layer-lift-meter-STUB.md:201,254 (BLOCKED:surface-close-adjudication-out-of-surface halted L1 before VERIFY on smoke-1 and smoke-3, on a task that bare solved 5/5 and L2 shipped). | D2 closure durability (durability-enforce): SKILL.md:276 (keep only the 'checkpoint + rerun' sentence); state-phase-write.py:1291-1560 (_surface_durability_ledger, enforce_closure_durability_reentry:1446 — reads phases.surface_close.post_sha, so it exists only for SURFACE_CLOSE); state-schema.md:65 durability[]. | D3 phase lifecycle + transition protocol for plan/probe/implement/surface/build/cleanup/final_report: SKILL.md:74-76, :100, :114, :282, :291, :302-306, :351, :361, :367-369 (spans); state-schema.md:73-118. Evidence: iterations/0075:135-141 (P-B: startup+interphase gaps are ≥50% of residual wall on 5/7 rows and 92-96% on clean rows); 0196-resolve-utility.md:37 (full/native 18.10×/7.31×/5.90×). | D4 deterministic complexity classifier + risk_profile keyword gate: SKILL.md:94 (classifier part), :96, :121; references/free-form-mode.md:7-71; state complexity/risk_profile/risk_probes_digest (state-schema.md:15-17,53,58-59). Evidence: CLAUDE.md:56 (domain labels and file count do not trigger); 0201-harness-transformation-plan.md:73 (no domain/file-count classifier or risk scorer). | D5 solo-headroom / solo-ceiling / pair-evidence halts and prompts: SKILL.md:94 (two halts), :175-184, :331 (hypothesis anchor), :359 (ideate guidance lines); free-form-mode.md:16-23, :58-59, :64-65, :80-81; verify.md:203-206; probe-derive.md:51-58. Evidence: user decision 5 (remove research vocabulary from runtime entry). | D6 pair_trigger reason telemetry + completeness validation + verify.coverage_failed: SKILL.md:327-329; verify.md:123-172; state-schema.md:70-71; verify-merge-findings.py:46-93, :123-138, :529-1106 (~650 lines). Evidence: verify.md:134 ("they no longer gate the second spawn"). Keep only the pair decision (eligible + skipped_reason ∈ {user_no_pair, auto_pair_other_engine_unavailable, mechanical_blocker}); see the KEEP record. | D7 phase-gated IMPLEMENT / plan '## Execution phases': SKILL.md:262-268, :257 (phase metadata sentence); plan.md:21; state-schema.md:62-63 (phases.implement.exec). Evidence: added by design in autoresearch/iterations/0037-plan-contract-handoff.md:51-95; grep 'phase-gated|Execution phases' over autoresearch/iterations found no measured-benefit record. | D8 FINISH_GATE: SKILL.md:355, :357 (precedence 1); state-schema.md:124,126; finish-gate.py (521, whole file). It duplicates the authorized_surface scope check (spec-verify-check.py:1742-1843) once that check also runs on the final source (MOVE in the spec-verify-check item). Two layers that catch the same bug should become one. | D9 final-report run-marker binding: SKILL.md:359-361; state-schema.md:100, :118, :130-138; state-phase-write.py final_report_digest:198-222; task-complete.py:246-247. The report becomes the owner's reply; the machine verdict is the merge output. | D10 Stop hook: resolve-stop-hook.py (359, whole file); bin/devlyn.js:896-923 (adds hook); state session_id (state-schema.md:50; resolve-bootstrap.py stamps it); terminal-claim-check.py classify_active_state (only caller is resolve-stop-hook.py:149). Evidence: autoresearch/DECISIONS.md:257 (0074.3: CLI caps the block loop at ~9 then exit 0; 'C1 = pressure, NOT absolute bind; C2 external classification stays the terminal authority'; codex route disabled). The hook also starts a Python process on every Claude Stop in every installed project. | D11 'Orchestrator does not write code': SKILL.md:22 (contradicts the owner kernel; 0202/0204). | D12 <harness_principles> and per-phase 'Read _shared/runtime-principles.md' rereads: SKILL.md:26-28; build-gate.md:73-75; cleanup.md:31-33; implement.md:33-40; verify.md:313-315; probe-derive.md tail. Evidence: autoresearch/iterations/0099-context-placement-ckf.md:385-390 (reread consumed 0/12 on opus-4-8 and 4/12 on opus-5). | D13 flags --bypass, --perf (+ state bypasses): resolve-bootstrap.py:22-27, :174-179; state-schema.md:66; README.md:84. No phases remain to bypass or time. A check that cannot run is reported as a limit. | D14 IMPLEMENT round-scoped prompt/session/receipt state binding and the DEVLYN_INVOCATION_* receipt path: SKILL.md:229-246; state-schema.md:99, :101; invocation-receipt.py start_receipt/finish_receipt/validate_receipt*:217-507 + tests; codex-monitored.sh:58-61, :123-149, :307. The consumer (state-phase-write do_complete) is deleted. Bypass/sandbox rejection stays in codex-monitored.sh:83-93, and the transport carrier (DEVLYN_CODEX_PROMPT_FILE) still records exact prompt, argv and exit. | D15 state criteria[]: state-schema.md:30-32, :68; resolve-bootstrap.py:473, :1026. grep shows no script reads it, and implement.md:20 contradicts 'workers never edit state' (implement.md:21). | D16 grok pair-judge anchor execution + grok-anchor-guard.py (78): adapters/grok.md:69-101. The anchor precedence starts from the solo-headroom command. In the kernel reviewers are read-only (verify.md:88) and the owner reproduces (R3). | D17 pair-plan-schema.md (298): its own header (line 3) marks it as an archive doc for the deleted auto-resolve plan-pair. Only lint Check 13 and benchmark scripts read it; hand it to the benchmark packet.

**Current behavior.** resolve runs PLAN → RISK_PROBES? → IMPLEMENT → SURFACE_CLOSE? → BUILD_GATE → CLEANUP → VERIFY → FINAL_REPORT (SKILL.md:21). State-machine spans are written through state-phase-write.py for every phase.

**Target behavior.** None of D1-D17 exists in config/skills/devlyn:intent or the shrunk _shared. Each deletion is listed in the PR body and the iteration note with the evidence above. Nothing is silently dropped: removed user-visible flags (--risk-probes, --no-risk-probes, --bypass, --perf) appear in the README migration table and fail as unknown flags (BLOCKED:invalid-flags from the existing bootstrap parser).

**Tests.** Delete lint Checks 6c2 (579-656) and 6e (1495-1508). Remove the SURFACE/durability/final-report/phase-lifecycle cases from the state-phase-write.py self-test (starts at :2260). Delete finish-gate.py and resolve-stop-hook.py with their self-tests. New model-free check: grep -rnE 'SURFACE_CLOSE|surface-close|probe-derive|risk_probes|pair_trigger.reasons|finish-gate|resolve-stop-hook|durability-enforce|Execution phases' config/skills .agents/skills returns nothing. The solo-headroom grep excludes devlyn:ideate until the research-vocabulary packet lands.

**Migration.** The public skill /devlyn:resolve disappears (see the installer item). Removed flags are listed in the README migration table. An in-flight schema-3.0 run cannot be continued by intent: the bootstrap's unfinished-run refusal (0118) stops it with guidance to finish it with the previous version or archive it explicitly.

**Risk.** HIGH blast radius (the whole full route changes) but mostly deletion. Main risk: silently losing a guarantee D1/D8 provided. Mitigation: a KEEP/MOVE item carries each surviving guarantee — scope via the final-source authorized_surface check, docs/tests via the owner plus the reviewer 'incorrect customer documentation is binding' rule (verify.md:97-104).

**Net lines.** ≈ −9,000 source lines before the .agents mirror doubling (mostly state-phase-write, verify-merge-findings, spec-verify-check self-tests and the 4 deleted files)

### 1. DECISION RECORD B — MOVE-TO-OWNER (keep the responsibility, drop the separate machinery)

**Change.** DECISION RECORD B — MOVE-TO-OWNER (keep the responsibility, drop the separate machinery)

**Files / lines.** M1 PLAN: SKILL.md:112-121; references/phases/plan.md:1-39. The owner writes .devlyn/plan.md before the first product edit: authorized_surface sentinel + json (plan.md:18, kept verbatim so spec-verify-check.py:1682-1715 still parses it), risks, verbatim acceptance. The digest is bound once through the shrunk writer (0112 R3: docs/specs/iter0112-verdict-authority-chain/spec.md:36-37,71-74). Scope is never widened afterwards (build-gate.md:54 'only sanctioned fix is removing the file'). | M2 IMPLEMENT: SKILL.md:223-260; references/phases/implement.md:1-44. The owner implements in its own context. When the frozen worker role, executor pin or --engine names a different engine (user decision 3: gpt-6-sol for implementation), the owner delegates the bounded edit through codex-monitored.sh (-s workspace-write, network false) and keeps the transport carrier and raw result (owner.md:15-19). Keep implement.md:24-30 quality bar (spec is the contract, red-first for bugs, existing tests are contract, no mocks replacing real IO, scope). Evidence: autoresearch/iterations/0204-intent-conformance.md:15-21 (one owner invocation; 42 commands; no separate PLAN/BUILD/CLEANUP call); 0205 (three Astra owners with reviewer-driven repair); 0202-owner-run-candidate.md:12-20. | M3 BUILD_GATE: SKILL.md:278-296; references/phases/build-gate.md:38-58 → owner check guidance (references/checks.md). Evidence: 0125/0202 already run BUILD as owner commands. | M4 CLEANUP: SKILL.md:298-306; cleanup.md:1-33. The owner removes its own run-owned generated artifacts and kills any dev server (SKILL.md:353). The final untracked/scope check moves into the final mechanical run. Evidence: 0196-resolve-utility.md:97 (final CLEANUP trees identical 14/14; spans 1,197.867 s); 0203-owner-repair-verification.md:12-22 (staged changes and skip-BUILD gaps: the final check must cover index + worktree + untracked). | M5 RISK_PROBES: SKILL.md:123-221; references/phases/probe-derive.md:1-276. The owner turns reviewer or self-found counterexamples into executable regression checks before repair (owner.md:28-31). The only positive evidence is benchmark-scale (NORTH-STAR.md:273: 3 fixtures, 'does not prove broad product superiority'), and the auto gate is a domain keyword classifier (see D4). | M6 SURFACE_CLOSE obligations (UVR-STALE, PATH-TEST: surface-close.md:15-18) → implement.md:17-18 (owner repairs references the diff invalidated and adds tests for changed paths) + verify.md:97-104 (incorrect customer documentation is a binding finding). | M7 free-form criteria: free-form-mode.md:73-85. The owner writes .devlyn/criteria.generated.md (Requirements / Out of Scope / sentinel Verification json or explicit pure_design) before the first edit. Keep :62-63 (large → ## Assumptions logged; zero scope signal → BLOCKED:large-needs-ideation). | M8 FINAL_REPORT: SKILL.md:349-361 → owner reply: merged verdict quoted verbatim, findings with closure evidence, remaining limits, delivery status kept separate, and per-call usage for owner/executor/reviewers with UNKNOWN where missing (owner.md:44-48; user decision 2: record usage only). | M9 IMPLEMENT process-evidence obligations: SKILL.md:250-255; implement.md:19. The owner runs process-evidence.py run --phase implement. Binding and verdict floor move to the review-round open (shrunk state writer) and the merge. | M10 terminal precedence: state-schema.md:120-128. The merged VERIFY verdict is the only success path; every halt is non-success.

**Current behavior.** PLAN, IMPLEMENT (fresh worker), BUILD_GATE, CLEANUP, RISK_PROBES, SURFACE_CLOSE obligations, the classifier and FINAL_REPORT are separate spans or workers with their own prompts, verdicts and state writes.

**Target behavior.** One owner context does M1-M8. The only separate model invocations are: (a) the executor delegation when the pinned or role worker differs from the owner, and (b) the independent reviewers. Checks are real project commands plus spec-verify-check, all captured through process-evidence.py. The owner reproduces every binding finding before repairing it, reruns the affected checks plus the full final mechanical run, and gets a fresh review of the new source (0203 rule: a later source change invalidates earlier PASS evidence).

**Tests.** Live acceptance traces (see acceptance_checks) must show no separate PLAN/BUILD/CLEANUP/SURFACE/probe model calls — this closes 0201 step 1 for the Claude-owner route (0204 only proved it for the Codex route). Model-free: a scoped-staging commit happens before review, and a repaired source reruns the final mechanical run before a new review (state-writer self-test: a review-round open after a HEAD change without new mechanical results → BLOCKED).

**Migration.** User-visible: a Claude Code run no longer spawns a separate Agent IMPLEMENT worker by default. Executor pins and role configs keep routing implementation (engines.json is unchanged).

**Risk.** MEDIUM. Owner-context implementation removes the fresh-worker context split. 0197/0198 found no fresh-context advantage for review, but implementation isolation was never ablated. Reviewer independence (fresh, read-only) is kept, and that is the independence the evidence supports.

**Net lines.** Doc: references/phases/{plan,implement,build-gate,cleanup,probe-derive,surface-close}.md (501 lines) → references/checks.md (~40) plus ~30 lines of owner prose in SKILL.md

### 2. DECISION RECORD C — KEEP (serves a kernel responsibility; cite the failure each item prevents)

**Change.** DECISION RECORD C — KEEP (serves a kernel responsibility; cite the failure each item prevents)

**Files / lines.** K1 hands-free, no mid-run prompts, assume-and-log: SKILL.md:19 (user binding feedback 'auto-resolve fully hands-free'; CLAUDE.md:65). | K2 explicit routes fail closed, automatic OTHER unavailable → reported solo: SKILL.md:20, :333-338; engine-preflight.md:9-12, :28-48 (R1; CLAUDE.md principle 1; 0193-role-config-failure.md:6-12, a dangling engines.json made defaults win). | K3 runtime_paths shared-dir anchor: SKILL.md:30-48 (bin/devlyn.js:438-443 iter-0040 stamp bug; lint 10a1 1739-1751). | K4 dispatch primitives, used only for executor delegation and reviewers: SKILL.md:54-56 (Claude Agent / codex-monitored.sh foreground, never background / omp task); codex-monitored.sh:5-14 (iter-0007/0008 stream starvation). | K5 --engine, executor pin, --role-config, per-role model/effort as argv: SKILL.md:57-58, :102-106 (user decision 3; 0123 role controls). | K6 explicit judge evidence (requested vs observed model): SKILL.md:108-110; judge-role-evidence.py (DECISIONS 2026-09-08/0133: truthful unknown identity, worker reroute rejection). | K7 modes free-form / --goal-file / --spec / --verify-only: SKILL.md:62-68 (0201:174-176: do not silently change spec, verify-only or engine semantics; --goal-file is the devlynd ResolveAdapter launcher contract, SKILL.md:65). | K8 bootstrap: exact-byte goal/spec identity, sibling spec.expected.json validation, external-diff capture, admission lock and unfinished-run refusal: SKILL.md:82-88; resolve-bootstrap.py (docs/specs/0118-concurrent-admission/spec.md:16: a second bootstrap archived an unfinished run). | K9 untracked baseline + authorized_surface scope check: SKILL.md:92; build-gate.md:54; spec-verify-check.py:1682-1843 (autoresearch/iterations/0187-intent-and-simplification.md:87-92, :172-186: scope violations drive NO-GO. Artifact checks cannot see outside-checkout temporal writes, so the report must state that limit instead of claiming execution compliance). | K10 zero-scope halt + Large ## Assumptions: free-form-mode.md:62-63 (CLAUDE.md:60). | K11 generated criteria carrier or explicit pure_design: free-form-mode.md:73-83; spec-verify-check.py:24-27 (0164-build-gate-failure-evidence.md:12-19: a missing carrier must reach the parent as FAIL). | K12 scoped-staging commit before review: SKILL.md:259 (the reviewed source is an exact commit; 0203:12-16 staged-change gap). | K13 capability denial → BLOCKED:build-env-underprovisioned, no widened retry: build-gate.md:9-35; SKILL.md:296 (docs/specs/iter0112-verdict-authority-chain/spec.md:38-40, :83-88). | K14 required-tools-unavailable separation (infra vs product): SKILL.md:295 → 2 sentences in checks.md (0201:75). | K15 MECHANICAL rerun on the final source, verdict floor from the sealed manifest: SKILL.md:323; verify.md:26-37 (iter0112 spec.md:25-30, :60-66; 0164:56-58: removing the verdict guard admits an incorrect PASS). | K16 fresh read-only findings-only reviewer with a clause and counterexample rubric: SKILL.md:325; verify.md:1-112 (0184-review-repair-comparison.md:60-71: 12/12 sealed sources passed the mechanical checker, yet review found the --out input-overwrite and the repair fixed it; 0196:57-62 / 0185 lock-release HIGH). No fresh reviewer → BLOCKED:fresh-context-unavailable (SKILL.md:53, :71). | K17 dual-judge default-when-available + --pair-verify (fail-closed promise) / --no-pair (explicit opt-out): SKILL.md:325-338; verify.md:114-218 — user-approved exception NORTH-STAR.md:269, :271; keep unless the user decides otherwise (see open questions; 0184:106-109). | K18 single parser/collector for OTHER-engine output; collector failure → pair BLOCKED: SKILL.md:331, :342; judge-output-parser.py; collect-codex-findings.py (iter-0082 narrated preamble, iter-0106 NDJSON terminal message). | K19 merge rule (HIGH/CRITICAL or MEDIUM verdict_binding:true binding; worst source; no vote counting; merge output is the only writer): SKILL.md:331, :342; verify.md:278-294 (scripts/lint-skills.sh:416-418: F23 pair HIGH stayed PASS_WITH_ISSUES). | K20 600 s judge wall bounds + timeout markers (primary → BLOCKED floor; pair → TIMEOUT, solo headline): SKILL.md:342; verify.md:231-238, :260-276 (docs/specs/iter0093-verify-timeout-budget, iter0113-primary-verify-budget). A wall-clock timeout is not a token budget, so it is compatible with user decision 2. | K21 constrained Windows judge reads: SKILL.md:340; codex-config.md:59-62 (windows-portability-3.1.1). | K22 max_rounds bound on review→repair: resolve-bootstrap.py:165 (default 4); SKILL.md:295, :347. Exhaustion stays non-success. | K23 deterministic archive script: SKILL.md:363 (iter-0033a Smoke 3: the agent claimed archive without moving files). | K24 outer-owner completion + outer loop: SKILL.md:80, :365; references/task-completion.md:1-144; references/outer-loop.md:1-23. | K25 state is the single verdict source; lifecycle fields are never hand-edited: SKILL.md:369; state-schema.md:111-113 (0113-layer-lift-meter-STUB.md:253: the orchestrator hand-wrote the terminal verdict when the writer refused; 0044 stale started_at).

**Current behavior.** These rules exist today inside resolve and _shared.

**Target behavior.** K1-K25 appear in devlyn:intent (SKILL.md or references/review.md, checks.md, task-completion.md, outer-loop.md) or in unchanged/shrunk _shared scripts, each worded once. VERIFY review stays non-bypassable for intent runs and is dual-engine by default when the OTHER engine is available.

**Tests.** Existing self-tests stay green: process-evidence, judge-output-parser (via collect), collect-codex-findings, role-config, judge-role-evidence, task-complete, archive_run, terminal-claim-check, spec-verify-check, verify-merge-findings. Lint Checks 6b1, 9, 10, 10a, 10a2 and 12 stay. 6b, 6g, 6i, 6i1, 6j, 10a0 and 10d are retargeted to intent paths (see the lint item).

**Migration.** NONE for behavior. Documentation paths move from devlyn:resolve to devlyn:intent.

**Risk.** LOW. The KEEP items are existing code paths.

**Net lines.** 0 (retained)

### 3. Create config/skills/devlyn:intent (kernel SKILL + 4 references) and delete config/skills/devlyn:resolve. Mirror both in the tracked .agents/skills.

**Change.** Create config/skills/devlyn:intent (kernel SKILL + 4 references) and delete config/skills/devlyn:resolve. Mirror both in the tracked .agents/skills.

**Files / lines.** DELETE config/skills/devlyn:resolve/** and .agents/skills/devlyn:resolve/**. ADD config/skills/devlyn:intent/SKILL.md (~130-150 lines). Frontmatter name: devlyn:intent plus a short description of when to use it (explicit intent/spec runs, queue drains, work whose interacting requirements exceed the current context). Keep :8-10 <pipeline_config>. Kernel prose adapted from autoresearch/experiments/0204/owner.md:8-48. Runtime paths block copied from SKILL.md:30-48. Routing condensed from :50-59 (owner = current CLI; delegate only to a pinned or role executor ≠ owner; --engine does not disable pairing; adapter-file extension). Modes/flags from :62-68 (keep --goal-file, --spec, --verify-only, --engine, --role-config, --pair-verify, --no-pair, --max-rounds; drop the others). Start = bootstrap + freeze roles + untracked baseline + announce (from :82-98 without the classifier/risk text). Explicit role dispatch condensed from :102-110. Scoped-staging commit from :259. Review loop from :323-347. Archive + outer owner from :363-365. A ~15-line 'State' section replaces state-schema.md. ADD references/review.md (~90-110 lines) from verify.md:1-112 + :179-218 (minus solo-headroom :203-206) + output contract; Codex/Claude invocation details stay in codex-config.md / adapters. ADD references/checks.md (~35-45 lines) from build-gate.md:9-35 (condensed), :38-58 (gates 1-3, 5; step 4 = spec-verify-check), :67-71, plus SKILL.md:295 condensed. git mv references/task-completion.md and references/outer-loop.md into devlyn:intent/references (edits in the delivery item; outer-loop.md:3 'full /devlyn:resolve run' → '/devlyn:intent run'). DELETE state-schema.md, free-form-mode.md and phases/* (content folded or deleted per decision records A/B). Principles: none restated. The SKILL references CLAUDE.md/AGENTS.md only, and review.md keeps only the evidence rules a read-only judge needs (D12).

**Current behavior.** config/skills/devlyn:resolve/: SKILL.md 369; references/state-schema.md 150, task-completion.md 144, free-form-mode.md 85, outer-loop.md 23; phases/verify.md 315, probe-derive.md 276, build-gate.md 75, implement.md 44, plan.md 39, surface-close.md 34, cleanup.md 33. Total 1,587 lines / 161,135 bytes. .agents/skills/devlyn:resolve/** is a byte-identical tracked copy (git ls-files .agents: 59 files).

**Target behavior.** /devlyn:intent is the only full-route entry. The whole model-read load set is ≤ ~40,000 bytes (SKILL.md ≤ ~16,000). It contains no token or usage budget, no phase names beyond 'review', and no research vocabulary (solo_claude, solo-headroom, S2-S6, pair-evidence, benchmark). The same state file .devlyn/pipeline.state.json and the same .devlyn artifact names are used so the retained _shared tools work unchanged.

**Tests.** lint Check 5 (name frontmatter) covers the new skill. The lint critical_path_files list (scripts/lint-skills.sh:58-106) replaces the 12 resolve entries with devlyn:intent/SKILL.md and references/{review,checks,task-completion,outer-loop}.md. Commands: diff -qr -x __pycache__ config/skills .agents/skills; wc -c config/skills/devlyn:intent/SKILL.md config/skills/devlyn:intent/references/*.md.

**Migration.** The installer purge and the README migration table cover users. The .claude/skills dev mirror in the checkout is gitignored (.gitignore:17) and must be refreshed locally so the lint Check 6 parity is meaningful.

**Risk.** MEDIUM. Prompt-only rules the orchestrator must follow (reproduce before repair, rerun the final mechanical run after changes) are backed by the state-writer refusals in the state item, not by prose alone.

**Net lines.** −1,587 + ~430 ≈ −1,150 (×2 with the .agents mirror)

### 4. State schema 4.0 and shrink state-phase-write.py to the single writer for the surviving state writes

**Change.** State schema 4.0 and shrink state-phase-write.py to the single writer for the surviving state writes

**Files / lines.** config/skills/_shared/state-phase-write.py (+ .agents mirror). Keep verbs: --freeze-roles (:1668-1683, unchanged); spawn/complete limited to phase ∈ {plan, verify}. plan complete binds the .devlyn/plan.md digest (reuse validate_plan_output/bind_plan_output :150-196) and every later write rehashes it (0112 R3). verify spawn = review-round open: clear_verify_round_artifacts (:1563); record round = rounds.global, primary engine from role_resolution, and pre_sha = HEAD (the reviewed commit); bind declared implement/build_gate process evidence (reuse bind_process_evidence :261-409); refuse when HEAD ≠ the source of the current mechanical results. verify complete keeps 'verdict owned by verify-merge-findings.py'. Delete: transition (:2074-2140), owner identity (:1594), implement/build/cleanup/probe/surface/final_report paths, durability, receipts binding, parse_effective_model (:937), and the corresponding self-test sections. Keep select_claude_primary_model (:891-934) because judge-role-evidence.py:50 imports it. Schema 4.0 fields — KEEP: version, run_id, started_at, engine, engine_source, mode, pair_verify, process_evidence, base_ref, rounds{max_rounds, global}, source{type, spec_path, spec_sha256, goal_path, goal_sha256, criteria_path, criteria_sha256}, role_resolution, role_config_input, role_no_pair, phases.plan{started_at, completed_at, verdict, output_sha256}, phases.verify{started_at, completed_at, round, engine, pre_sha, verdict, sub_verdicts, merged, role_evidence, pair (eligible + skipped_reason)}. DELETE: session_id, complexity, risk_profile (--no-pair is carried by role_no_pair), risk_probes_digest, bypasses, implement_passed_sha, criteria[], verify.coverage_failed, verify.pair_trigger.reasons, per-phase triggered_by/execution_kind/invocation_receipt/post_sha/judge_durations_ms/history, phases.{probe_derive, implement, surface_close, build_gate, cleanup, final_report}.

**Current behavior.** state-phase-write.py has 5,663 lines (non-test ~2,260; self-test from :2260). It covers spawn/complete/transition for 8 phases, owner identity (:1594), PLAN output binding (:150-196), process-evidence binding (:261-409), SURFACE adjudication/rollback/durability (~:470-1560), invocation-receipt binding, freeze-roles (:1668), final_report_digest (:198) and clear_verify_round_artifacts (:1563). Schema: state-schema.md:5-45, :47-110.

**Target behavior.** Every state write goes through one sanctioned writer (0113 smoke-3: when no writer exists, orchestrators hand-edit). A plan change after binding blocks the next state write. A review round cannot open on a source that differs from its sealed mechanical results. Halts before review record the verdict through 'spawn --phase verify' + 'complete --phase verify --verdict BLOCKED', so terminal-claim-check classifies them as CLEAN-with-BLOCKED instead of INCOMPLETE; the reason goes in the report.

**Tests.** Rewrite the state-phase-write.py --self-test: freeze-roles snapshot; plan bind + tamper → block; verify spawn clears round artifacts; HEAD ≠ mechanical source → block; duplicate-key/NaN rejection kept (0112 R2); BLOCKED halt completion; v3 state refused with an explicit message. scripts/test-owner-phases.py (238): keep only the plan-immutability and final scope with staged + untracked cases (0203) and delete the BUILD/CLEANUP/repair-edge cases. Lint 6c1 (572-578) keeps running it.

**Migration.** Schema 3.0 active runs are refused by the bootstrap/writer with guidance. Archived 3.0 runs stay on disk but are not deliverable through the new pipeline acceptance (document this in README).

**Risk.** HIGH. This is the most coupled change: process-evidence, spec-verify-check, verify-merge, archive, terminal-claim-check and task-complete all read state. Land it as the first commit in the PR, with consumers updated in the same PR.

**Net lines.** 5,663 → ~1,000-1,300 (≈ −4,400; ×2 mirror)

### 5. Map _shared to KEEP/SHRINK/DELETE with line counts, orphan analysis and resulting size

**Change.** Map _shared to KEEP/SHRINK/DELETE with line counts, orphan analysis and resulting size

**Files / lines.** DELETE (orphaned by DELETE items): finish-gate.py 521 (D8); resolve-stop-hook.py 359 (D10); grok-anchor-guard.py 78 (D16); pair-plan-schema.md 298 (D17, goes to the benchmark packet) = −1,256. SHRINK: state-phase-write.py 5,663 → ~1,200 (state item). spec-verify-check.py 5,736 → ~4,500 (risk-probe functions ~417 non-test lines incl. --validate-risk-probes/--print-risk-probes-digest/--include-risk-probes/tag markers, risk_profile checks :1140-1170, their self-tests; see the spec-verify item). verify-merge-findings.py 3,437 → ~2,200 (D6 + risk_profile :656-691 + solo-headroom :778-845 + v2.0 primary_judge_blocker replay; self-tests). resolve-bootstrap.py 1,410 → ~1,200, renamed to intent-bootstrap.py (drop --risk-probes/--no-risk-probes/--bypass/--perf, session_id stamp, criteria[] and phase skeleton; keep the admission lock, goal/spec identity, role-config staging, external diff; optionally call freeze-roles). archive_run.py 957 → ~800 (PER_RUN_PATTERNS minus surface-close.*, probe-derive.*, risk-probes.jsonl, probes/, cleanup.*, finish-gate.*, final-report.md, phase prompt/worker-session/receipt families; the docstring 'Archive devlyn:resolve run artifacts' changes, pinned by lint 6c1 :553-571). terminal-claim-check.py 552 → ~380 (PHASE_ORDER :23-32 → (plan, verify); delete classify_active_state, terminal_halt_witness/HALT_WITNESS_PHASES :34-39, and the final_report requirement; CLEAN = verify completed with a valid verdict + archived). task-complete.py 1,450 → ~1,380 (pipeline_acceptance :222-296 against the shrunk evidence; default mode :175). invocation-receipt.py 1,230 → ~800 (D14 receipt path; keep dispatch/transport :128-215, :1125-1175). codex-monitored.sh 313 → ~280 (D14 env block). phase-prompt-render.py 183 → ~165: delete the PLAN-only validate_plan_context (:30-43) and wire it into intent for review prompts (adapter minus ## Invocation/## Role eligibility + review.md + context → exact bytes + sha), following 0201-harness-transformation-plan.md:65. Today it is orphaned in the product (only caller: benchmark/ceiling/scripts/plan-dispatch-oracle.py). process-evidence.py 926 → ~930 (phase_round :241-246 reads state.rounds.global instead of a per-phase span, because owner checks no longer have spans). expected.schema.json 205 → ~190 (drop required_risk_probe_requirements :183-205). codex-config.md 81 → ~60, engine-preflight.md 61 → ~40, adapters 314 → ~230 (docs item). runtime-principles.md 101 → 101 (pointer edits only; ideate + lint 12 still need it). KEEP unchanged: platform-support.py 373, run-bounded.py 58, judge-output-parser.py 200, collect-codex-findings.py 505, role-config.py 566, judge-role-evidence.py 300, engine-doctor.sh 110, .ruff.toml.

**Current behavior.** config/skills/_shared top-level: 25,673 lines / 1,217,034 bytes; adapters: 314 lines / 20,843 bytes. Total 25,987 lines.

**Target behavior.** _shared ≈ 16,000-17,000 lines (−35-38%), most of it self-tests. Model-read _shared docs + adapters ≈ 45 KB (from ~53 KB, excluding pair-plan-schema). Intent skill ≈ 430-470 lines / 35-40 KB versus resolve 1,587 / 161,135 bytes. No retained script references a deleted file (check: grep -rn -E 'finish-gate|resolve-stop-hook|grok-anchor-guard|pair-plan-schema|state-phase-write.py\"\]\[\"(final_report_digest|parse_effective_model)' config/skills).

**Tests.** Every retained script's --self-test passes. test-windows-portability.py cases touching deleted/changed APIs are updated (tests item).

**Migration.** Installed _shared is fully replaced on reinstall (bin/devlyn.js cleanManagedSkillDirs :474-491 and installSkillsForCLI :664-715), so deleted files vanish from installs. The Stop hook needs explicit settings migration (installer item).

**Risk.** MEDIUM. Hidden cross-imports via runpy (e.g. task-complete.py:246 → state-phase-write.final_report_digest; judge-role-evidence.py:50 → state-phase-write.select_claude_primary_model; finish-gate → spec-verify-check). The grep above plus the self-tests catch them.

**Net lines.** ≈ −9,300 lines (×2 with the .agents mirror)

### 6. spec-verify-check.py + expected.schema.json: remove risk probes, enforce scope on the final source, verify the bound plan digest

**Change.** spec-verify-check.py + expected.schema.json: remove risk probes, enforce scope on the final source, verify the bound plan digest

**Files / lines.** config/skills/_shared/spec-verify-check.py: 5659-5664 (run authorized_surface_findings in verify_mechanical too, except mode verify-only/external-diff); load_authorized_surface :1682-1715 (compare the plan.md sha256 with state.phases.plan.output_sha256 → scope.authorized-surface-malformed CRITICAL on mismatch); remove risk-probe code paths and CLI modes (main :5175-5200 flags --include-risk-probes/--validate-risk-probes/--print-risk-probes-digest; :703-710 digest; :1140-1170 risk_profile) and their self-test sections (~324 'probe' lines after :1982). Leave the solo-headroom --check/--check-expected validation for the research-vocabulary packet, because ideate still emits it. config/skills/_shared/expected.schema.json:183-205 (delete required_risk_probe_requirements). config/skills/devlyn:ideate/references/spec-template.md:103 (delete the bullet). docs/specs/devlyn-history-lifecycle/spec.expected.json:39 (remove the field from this planned spec so --check-expected still passes). Mirror to .agents.

**Current behavior.** The authorized_surface scope check runs only in the BUILD_GATE phase (spec-verify-check.py:5659-5664: 'if output_phase() == "build_gate" and base_sha'), so FINISH_GATE re-checks the final diff. Risk-probe staging, validation and digest are built in. expected.schema.json accepts required_risk_probe_requirements (:183-205).

**Target behavior.** The final mechanical run on the final source enforces verification commands, forbidden patterns, required/forbidden files and scope against the bound plan: tracked + staged + created-untracked versus the baseline, .devlyn exempt. Scope creep introduced during repair is caught without FINISH_GATE. A plan edited after binding fails closed.

**Tests.** spec-verify-check.py --self-test: new cases for scope violation detected in the verify_mechanical phase, a plan digest mismatch, and verify-only skipping scope. Delete the risk-probe self-tests. Lint 6d (657-895): keep the self-test invocation plus the complexity/generated-criteria/malformed-expected pins; delete the risk-probe tag/marker pins. Lint 6g (1293-1322) and 6i (1323-1349) are retargeted to intent paths. Run: python3 config/skills/_shared/spec-verify-check.py --check-expected docs/specs/devlyn-history-lifecycle/spec.expected.json → exit 0.

**Migration.** A user spec.expected.json that declares required_risk_probe_requirements fails --check-expected with 'unsupported field'. README migration notes that the field is removed.

**Risk.** MEDIUM. This is the largest script. Keep the BENCH_WORKDIR branch until the benchmark packet decides; do not delete it here.

**Net lines.** ≈ −1,200 (×2 mirror)

### 7. verify-merge-findings.py: keep only the verdict core

**Change.** verify-merge-findings.py: keep only the verdict core

**Files / lines.** config/skills/_shared/verify-merge-findings.py: delete :46-93 (ALLOWED/KNOWN reasons, headroom markers except the minimal pair skip set), :123-138, :529-1106 (pair_trigger_* / risk_profile / spec_frontmatter_complexity / solo-headroom / outcome_independent_reasons / completeness), and the matching self-test sections from :1471. Keep: loads_strict_json, rank/worse, finding_rank, mechanical_evidence_* (:150-245, the manifest-derived floor per 0112 R1), primary/pair timeout markers (:254-326, :1107-1145), read_findings, canonical_other_judge_stdout and pair capture checks, detect_pair_stdout_contract_violations (:1181-1372), write_outputs/write_state. Add in place: 'pair required' derivation = OTHER available ∧ ¬role_no_pair ∧ ¬mechanical_blocker (from state.phases.verify.pair) — missing pair output then stays BLOCKED, never solo PASS. Mirror to .agents.

**Current behavior.** 3,437 lines (non-test ~1,470). It includes pair_trigger reason completeness/unknown/skip validation, risk_profile shape checks, complexity/solo-headroom reason derivation, v2.0 primary_judge_blocker replay, role-evidence binding and the timeout markers.

**Target behavior.** Merged verdict = worst of (the mechanical floor from the sealed manifest, primary findings, pair findings or TIMEOUT). HIGH/CRITICAL or MEDIUM verdict_binding:true → NEEDS_WORK. A missing required source → BLOCKED. The merge is the only writer of verify-merged.findings.jsonl / verify-merge.summary.json / phases.verify.{verdict, sub_verdicts, merged}.

**Tests.** verify-merge-findings.py --self-test keeps: F23 pair HIGH binding, emptied mutable results cannot upgrade (0112 R1), NaN/duplicate keys, primary timeout floor, pair TIMEOUT semantics, collector failure → BLOCKED, and new 'pair required but absent → BLOCKED'. Lint 6b (420-503): replace the ~40 grep pins with self-test + 6 pins (reject_json_constant, loads_strict_json, mechanical floor, pair-required, timeout markers). The .agents risk_profile guard loop (:486-502) is deleted.

**Migration.** NONE (no user-facing surface).

**Risk.** MEDIUM. Deleting telemetry must not remove the pair-required fail-closed path (the explicit new self-test guards it).

**Net lines.** ≈ −1,200 (×2 mirror)

### 8. Bootstrap, archive, terminal classification, delivery default and receipt/transport cleanup

**Change.** Bootstrap, archive, terminal classification, delivery default and receipt/transport cleanup

**Files / lines.** git mv config/skills/_shared/resolve-bootstrap.py → intent-bootstrap.py (docstring :2; VALUE_FLAGS/BOOL_FLAGS :22-25; VALID_BYPASSES/PHASE_NAMES :27-31; parse_flags :114-195; skeleton :440-490; self-test updates :926-1380). config/skills/_shared/archive_run.py (PER_RUN_PATTERNS and dynamic validators; docstring pinned by lint :553-571). config/skills/_shared/terminal-claim-check.py:23-39 and :100-260. config/skills/_shared/task-complete.py:175 (return override or value or "pr"); :222-296 pipeline acceptance: phases (plan, verify), source_sha == phases.verify.pre_sha, drop final_report_digest/finish-gate checks, keep the merge summary + mechanical carrier PASS + declared process-evidence validation; self-tests around :1046-1070 and :1111-1330 (fixture archive without finish-gate/final-report). config/skills/devlyn:intent/references/task-completion.md:68-78 (pipeline acceptance fields), :95-106 (default pr; auto = explicit opt-in). config/skills/_shared/invocation-receipt.py:217-507 + receipt self-tests :784-1124; codex-monitored.sh:58-61, :123-149, :307 (D14). config/skills/_shared/judge-role-evidence.py unchanged. Mirror all to .agents.

**Current behavior.** resolve-bootstrap.py accepts 12 flags (:22-27) and stamps session_id + criteria[] + an 8-phase skeleton (:27-31, :473). archive_run.py archives resolve artifact families. terminal-claim-check requires final_report + archive. task-complete.py pipeline_acceptance requires plan/implement/cleanup/verify/final_report/build_gate spans, cleanup.post_sha, final report digest and finish-gate summary (:236-250), and defaults to mode 'auto', which requests gh pr merge --auto (:175, :640-676).

**Target behavior.** The intent bootstrap accepts exactly --goal-file, --spec, --verify-only, --engine, --role-config, --pair-verify, --no-pair, --max-rounds and positional goal text. Anything else → BLOCKED:invalid-flags. A delivered task defaults to push + PR with no auto-merge request (user decision 4: '작업 후에 자동 PR 까지만'). An explicit devlyn.completionMode auto or --mode auto keeps working. Delegated Codex executor evidence = transport carrier + raw stdout/stderr + exit.

**Tests.** intent-bootstrap.py --self-test (flag matrix :1054-1100 updated; removed flags rejected). task-complete.py --self-test: new case 'no --mode and no config → PR created, no gh pr merge call'. archive_run.py and terminal-claim-check.py --self-test (0195 type guard and 0200 '..' run_id cases kept). invocation-receipt.py --self-test (transport cases kept). Lint 6b2 (517-531): keep the codex-monitored.sh bypass/danger-full-access pins and drop the receipt pins.

**Migration.** Projects with no devlyn.completionMode now stop at a PR instead of requesting auto-merge. Announce this in README/CHANGELOG. Explicit 'auto' is preserved.

**Risk.** MEDIUM. The delivery default flip changes observable behavior for existing projects without a local completionMode.

**Net lines.** ≈ −850 (bootstrap −200, archive −150, terminal −170, task-complete −70, receipt −430, wrapper −35; +~200 moved/rewritten tests) ×2 mirror

### 9. _shared routing docs and adapters: retarget to intent, delete phase/probe/solo-headroom text

**Change.** _shared routing docs and adapters: retarget to intent, delete phase/probe/solo-headroom text

**Files / lines.** config/skills/_shared/codex-config.md:25, :35-58, :79-81. config/skills/_shared/engine-preflight.md:3-36 (drop the risk-probe explicit/automatic classes, the 'PLAN remains orchestrator-fixed' wording and the SURFACE text; the worker role = executor delegation; the freeze step = bootstrap/state writer). config/skills/_shared/adapters/{omp.md:5-13, claude.md:92, grok.md:56-101 (read-only tools read_file/grep/list_dir, no run_terminal_cmd, no anchor), codex.md (remove the repo-specific mirror tactic), README.md:68-71 (phase-prompt-render projection)}. config/skills/_shared/runtime-principles.md:3, :97 plus :70 and :85, changed identically to CLAUDE.md:129 and :152 (lint Check 12 parity, scripts/lint-skills.sh:4014-4106). Mirror to .agents.

**Current behavior.** codex-config.md:25, :35, :79 describe resolve VERIFY pair-mode and IMPLEMENT. engine-preflight.md:3, :7, :11-12, :16-24, :36 describe PLAN/BUILD/risk-probes/freeze via state-phase-write. adapters/omp.md:5, :9-13 cover phase workers and state writes. adapters/claude.md:92 names 'canonical resolve JUDGE_STEM'. adapters/grok.md:69-101 covers the anchor and guard hook. adapters/codex.md contains the devlyn-repo-specific '.agents mirror' retrieval tactic. adapters/README.md:68-71 describes runtime injection. runtime-principles.md:3, :70, :85, :97 name resolve.

**Target behavior.** The shared docs describe only the intent kernel roles: owner, executor delegation, primary/pair reviewer. Grok reviews read-only, and a collector failure is still BLOCKED.

**Tests.** Lint 10a (1642-1738): drop the probe-derive needle and keep the isolation checks. Lint 10b (1785-1799): update the wording to devlyn:ideate/devlyn:intent. Lint 10d (1822-1858): intent SKILL path. Lint 12 still passes.

**Migration.** NONE

**Risk.** LOW-MEDIUM. The grok reviewer's quality without anchor execution is unmeasured (open question).

**Net lines.** ≈ −130 (×2 mirror)

### 10. Other skills that reference resolve: queue, engines, ideate, standards skills

**Change.** Other skills that reference resolve: queue, engines, ideate, standards skills

**Files / lines.** config/skills/devlyn:queue/SKILL.md:24, :34-36, :37 ('verify/build-gate exhaustion' → 'review exhaustion'), :41. config/skills/devlyn:engines/SKILL.md:6, :33 ('PLAN … never follows the pin' → 'the owner plans; the executor pin routes implementation edits'), :34 (drop 'risk-probe'). config/skills/devlyn:ideate/SKILL.md:3, :6, :13, :67-68 (drop the PLAN→…→VERIFY enumeration and the spike 'relaxed VERIFY'), :115, :149, :151, :159; references/elicitation.md:108, :141; from-spec-mode.md:46, :69; project-mode.md:39, :66-67, :77, :87; spec-template.md:3, :12 (stale claim: 'resolve's CLEANUP flips to done' — grep shows no status write in resolve/cleanup.md; replace with 'the outer owner updates status' or delete). Standards skills: root-cause-analysis/SKILL.md:11, :65 (also a stale 'pair-judge fires conditionally on high-risk' claim); code-health-standards/SKILL.md:11; ui-implementation-standards/SKILL.md:73. Mirror all to .agents.

**Current behavior.** devlyn:queue/SKILL.md:24, :34-36, :41 point to ../devlyn:resolve/references/* and run /devlyn:resolve. devlyn:engines/SKILL.md:6, :33-34 name resolve PHASE 0, 'PLAN is orchestrator-fixed' and 'VERIFY/risk-probe time'. Ideate announces /devlyn:resolve --spec (SKILL.md:3, :6, :13, :67-68, :115, :149, :151, :159; references/elicitation.md:108, :141; from-spec-mode.md:46, :69; project-mode.md:39, :66-67, :77, :87; spec-template.md:3, :12). root-cause-analysis/SKILL.md:11, :65; code-health-standards/SKILL.md:11; ui-implementation-standards/SKILL.md:73.

**Target behavior.** Every live reference points to /devlyn:intent and devlyn:intent/references/{outer-loop,task-completion}.md. Solo-headroom paragraphs in ideate are left for the research-vocabulary packet.

**Tests.** grep -rn 'devlyn:resolve' config/skills .agents/skills returns nothing. Lint 6f (896-1292): delete the resolve-side pins ('resolve risk-probe prompts…', 'resolve pair-JUDGE prompts…', 'resolve VERIFY docs…/pair trigger…', 'resolve free-form mode must block…') and keep the ideate pins.

**Migration.** NONE

**Risk.** LOW. Text edits, but they overlap the frontmatter-fix and research-vocabulary packets (merge conflicts).

**Net lines.** ≈ −10 (text swaps; ×2 mirror)

### 11. Installer bin/devlyn.js + package.json: install intent, purge resolve, remove the legacy Stop hook safely

**Change.** Installer bin/devlyn.js + package.json: install intent, purge resolve, remove the legacy Stop hook safely

**Files / lines.** bin/devlyn.js:18 ('devlyn:resolve' → 'devlyn:intent'); :134-181 (add 'skills/devlyn:resolve' with a dated comment); :896-923 (replace the add with: remove every hooks.Stop entry whose hooks array contains exactly that legacy command, preserve all other entries, drop hooks.Stop only if the removal left it empty and it was created by devlyn — otherwise keep []); :925 log text; :250, :663, :725, :858 wording. package.json:4 (description: drop 'phase-gated pipelines'); package.json:79 (keep scripts/test-owner-phases.py only if the file is kept). Recommend a version bump to 4.0.0 at release (removal of a public skill; lint 9b tag parity at release time).

**Current behavior.** DEVLYN_CORE_SKILLS (:18) installs devlyn:resolve. DEPRECATED_DIRS (:134-181) has no resolve entry. The settings merge adds the Stop hook 'python3 "$CLAUDE_PROJECT_DIR/.claude/skills/_shared/resolve-stop-hook.py"' (:904-923). Messages at :250, :663, :725, :858 and :925 name resolve.

**Target behavior.** An upgrade removes .claude/skills/devlyn:resolve (and the ~/.codex/skills and ~/.agents/skills copies via cleanupDeprecated), installs devlyn:intent, and removes the exact legacy Stop hook. Removing the hook is required: once resolve-stop-hook.py is deleted, the hook command 'python3 <missing file>' exits 2, and Claude Code treats a Stop-hook exit 2 as a block, so every stop would be blocked until the loop cap.

**Tests.** test-windows-portability.py: invert :265 (assert the legacy hook is absent and a user-added Stop hook survives); :318-335 install asserts devlyn:intent and the resolve purge; :705-735 alias tests use devlyn*intent. New temp-project check: pre-seed a legacy hook + another hook + an old devlyn:resolve dir → node bin/devlyn.js -y → verify. Lint 5b (:369-370) paths devlyn:resolve → devlyn:intent; lint 5a unchanged.

**Migration.** Automatic on reinstall. Projects that are not reinstalled keep the old skill + hook + script together (consistent). The CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING lines (:932-935) belong to the installer-env packet (same file; coordinate).

**Risk.** HIGH if the hook removal is missed: every stop blocks in every upgraded project. Covered by the explicit test above.

**Net lines.** ≈ +10 / −12

### 12. CLAUDE.md / AGENTS.md managed text (installed template) + runtime-principles parity + instruction fingerprints

**Change.** CLAUDE.md / AGENTS.md managed text (installed template) + runtime-principles parity + instruction fingerprints

**Files / lines.** CLAUDE.md:13 (drop the --risk-probes/--no-risk-probes clauses); :27; :31; :34 (Quick Start 2 → /devlyn:intent; flags; 'owner implements, checks, independent dual review, repair'); :43-44 (Executor row; Pair judge row without risk probes); :50 (via /devlyn:intent); :54 (task-completion path 'relative to the installed devlyn:intent skill's directory'); :56 ('Use /devlyn:intent automatically only when…'); :58-63 (handoff steps; step 4 'review exhaustion'); :65 (outer-loop path config/skills/devlyn:intent/references/outer-loop.md); :129 and :152 (parity sections, identical edit in runtime-principles.md:70, :85); :167 (intent state); :168; :172 (skill surface: intent + ideate + design-ui + engines + queue; delete the unimplemented security-review claim); :174 (browser checks run by the intent owner). AGENTS.md: the same semantics at :13, :30, :34, :39, :41, :43, :45. After committing: node scripts/update-instruction-templates.js → bin/instruction-templates.json 'paragraphs' refreshed (no change to legacy template entries).

**Current behavior.** CLAUDE.md:13, :27, :31, :34, :43-44, :50, :54, :56, :58-63, :65, :129, :152, :167-168, :172, :174 and AGENTS.md:13, :30, :34, :39, :41, :43, :45 describe /devlyn:resolve phases, risk probes, 'Legacy executor', 'PLAN is orchestrator-fixed' and the resolve task-completion path. CLAUDE.md:172 also claims 'security review (delegated to the native security-review skill from BUILD_GATE)'; grep 'security' in config/skills/devlyn:resolve finds only the risk keyword list at SKILL.md:96, so that delegation is not implemented (stale claim).

**Target behavior.** Installed managed blocks route full work to /devlyn:intent and mention no removed flags or phases. The executor pin still binds conversational direct work (CLAUDE.md:50 semantics kept).

**Tests.** Lint 12 (4014-4106) parity passes. Lint 6k (1455-1485) rewritten to pin the new owner/executor wording in intent SKILL, CLAUDE.md, AGENTS.md and engines, including .agents. Lint 10c (1800-1821) extended so '/devlyn:resolve' outside the README legacy-surface-map block is flagged. test-windows-portability.py instruction tests (:341-705) still pass (the managed block is replaced by digest ownership, bin/instructions.js:14-18).

**Migration.** Users' managed blocks update on reinstall; custom text outside the block is preserved (bin/instructions.js).

**Risk.** MEDIUM. Merge conflicts with the research-vocabulary / principles packets that edit the same files. Land in a defined order.

**Net lines.** ≈ −20 to −40

### 13. README.md: replace the resolve section with intent, add migration mapping

**Change.** README.md: replace the resolve section with intent, add migration mapping

**Files / lines.** README.md:39, :42, :52, :61, :63-110 (new '/devlyn:intent' section: kernel in ~8 lines, 3 modes, kept flags, delivery default = PR, no auto-merge); :87-98 (delete); :114; :116-158 (roles: owner / executor / primary + pair reviewer; delete risk probes); :250-259 (add rows: '/devlyn:resolve' → '/devlyn:intent'; removed flags --risk-probes/--no-risk-probes/--bypass/--perf; kept flags; removed spec field required_risk_probe_requirements; the Stop hook is removed on reinstall); :316 (playwright → intent browser checks); :318; :329; :354.

**Current behavior.** README.md:39, :42, :52, :61, :63-110 (resolve modes/phases/flags, solo-headroom paragraphs :87-98, delivery default auto :100-109), :114, :116-158 (roles with PLAN/BUILD/risk-probe wording), :250-259 (legacy map), :316, :318, :329, :354.

**Target behavior.** User-facing docs match the shipped surface, and the migration is explicit (0201:174-176).

**Tests.** Lint 10c (1800-1821) and lint 1/2/3/9 pass. grep -n 'devlyn:resolve' README.md matches only the legacy-map rows.

**Migration.** Documents the migration.

**Risk.** LOW

**Net lines.** ≈ −60 to −100

### 14. scripts/lint-skills.sh: retarget and shrink the resolve pins

**Change.** scripts/lint-skills.sh: retarget and shrink the resolve pins

**Files / lines.** scripts/lint-skills.sh:54-106 (critical_path_files: remove the 12 devlyn:resolve entries, _shared/resolve-stop-hook.py, _shared/pair-plan-schema.md; rename resolve-bootstrap.py → intent-bootstrap.py; add the devlyn:intent SKILL + 4 references; also add phase-prompt-render.py). :420-503 (6b shrink). :517-531 (6b2 shrink). :553-571 (6c1 archive pins). :572-578 (6c1 owner phases: shrunk test). :579-656 (6c2 DELETE). :657-895 (6d: delete risk-probe pins). :896-1292 (6f: delete resolve-side pins). :1293-1454 (6g/6i/6i1/6j retarget to intent/SKILL.md + references/review.md; drop pair_trigger/phase pins). :1455-1485 (6k rewrite). :1495-1508 (6e DELETE). :1576-1641 (10a0 retarget: Codex primary review bounded + timeout marker). :1642-1738 (10a: drop the probe needle). :1785-1821 (10b/10c wording + the /devlyn:resolve guard). :1822-1858 (10d path). :369-370 (5b). Leave Checks 10d1, 10e (1902-3967), 13, 14, 15 and the collector-contract call at :539-545 to the benchmark packet.

**Current behavior.** 4,265 lines, 1,766 'resolve' mentions. The resolve-specific checks are spread across 6b, 6c1, 6c2, 6d, 6e, 6f, 6g, 6i, 6i1, 6j, 6k, 10a0, 10a, 10b, 10c, 10d and the critical_path list.

**Target behavior.** Lint encodes behavioral contracts for intent (merge binding, mechanical floor, scope on the final source, pair required ⇒ BLOCKED when absent, isolation, shared-dir anchor, parity) instead of pinning resolve prose.

**Tests.** bash scripts/lint-skills.sh exits 0. A deliberately reintroduced 'SURFACE_CLOSE' string in intent SKILL.md or a deleted merge pin makes it fail (spot mutation check).

**Migration.** NONE

**Risk.** MEDIUM. Over-deleting pins could drop real guards. Rule: replace a prose pin with a self-test call wherever a script owns the behavior.

**Net lines.** ≈ −400 to −600

### 15. Tests and CI

**Change.** Tests and CI

**Files / lines.** scripts/test-owner-phases.py (shrink to plan-binding immutability + final scope incl. staged/untracked per 0203; delete the BUILD/CLEANUP/repair-edge cases, or delete the file and move these cases into the state-writer self-test; keep package.json:79 consistent). scripts/test-windows-portability.py:141-190 (terminal-claim cases: CLEAN without final_report), :237-270 (Stop hook inverted), :318-335, :705-735 (intent names + resolve purge), :834-894 (archive patterns), :990-1060 (intent-bootstrap path; locks/junction kept), :1889-1972 (drop the receipt validate_receipt_artifacts/validate_receipt cases :1936-1941 and the finish-gate summary fixture :1957; archived transport completion kept). .github/workflows/portability.yml:44 (python3 config/skills/_shared/intent-bootstrap.py --self-test). scripts/static-ab.sh:5-40 (retarget the load-set list to devlyn:intent files).

**Current behavior.** scripts/test-owner-phases.py (238) exercises PLAN/BUILD/CLEANUP owner spans. scripts/test-windows-portability.py (2,081) exercises the resolve bootstrap, Stop hook, terminal-claim, archive, receipts and finish-gate summary. .github/workflows/portability.yml:44 runs resolve-bootstrap.py --self-test.

**Target behavior.** CI proves the retained contracts on POSIX and native Windows. There are no token or usage budgets in any test (user decision 2). Live smoke records usage only.

**Tests.** python3 scripts/test-windows-portability.py (POSIX portion locally; the full matrix in CI). The portability workflow is green on the PR.

**Migration.** NONE

**Risk.** MEDIUM. Windows-only paths (junctions, native locks) can only be proven in CI.

**Net lines.** ≈ −200 (test-owner-phases −150, portability −90, new installer migration case +40)

### 16. Evidence record and live acceptance (research docs only; no runtime vocabulary)

**Change.** Evidence record and live acceptance (research docs only; no runtime vocabulary)

**Files / lines.** autoresearch/iterations/<next-free-number>-intent-kernel.md (new: prediction before the smoke runs, raw results after, deleted components with evidence, residual limits). autoresearch/DECISIONS.md (one appended line). Keep autoresearch/NORTH-STAR.md:269-271 truthful: VERIFY/JUDGE pair default kept; 'resolve remains solo for PLAN/…' → 'intent owner is solo; review is dual by default'.

**Current behavior.** 0201 step 1 is proven only for the Codex owner route (0204). No trace exists of a Claude-owner intent run or of the installed skill.

**Target behavior.** The change is recorded with falsifiable predictions, for example: 'no PLAN/BUILD/CLEANUP/SURFACE/probe model call appears in the owner trace'; 'the seeded 0184-class input-overwrite defect is found by review, reproduced, repaired and rechecked'; 'a verify-only run never publishes'. Actual usage per call is recorded, with UNKNOWN allowed.

**Tests.** See acceptance_checks (live smoke).

**Migration.** NONE

**Risk.** LOW

**Net lines.** +60 to +90 (autoresearch only)

## Acceptance checks

- cd /Users/aipalm/.local/share/nx01/core-continuation-20260912 && test ! -e config/skills/devlyn:resolve && test ! -e .agents/skills/devlyn:resolve && test -f config/skills/devlyn:intent/SKILL.md
- diff -qr -x __pycache__ config/skills .agents/skills   # exit 0
- bash scripts/lint-skills.sh   # exit 0
- for s in state-phase-write spec-verify-check verify-merge-findings intent-bootstrap archive_run terminal-claim-check task-complete invocation-receipt process-evidence collect-codex-findings role-config judge-role-evidence; do python3 config/skills/_shared/$s.py --self-test || exit 1; done
- python3 scripts/test-owner-phases.py   # if the file is kept
- python3 scripts/test-windows-portability.py   # POSIX portion; full POSIX + native Windows matrix via .github/workflows/portability.yml on the PR
- python3 config/skills/_shared/spec-verify-check.py --check-expected docs/specs/devlyn-history-lifecycle/spec.expected.json   # exit 0 after removing required_risk_probe_requirements
- ! grep -rnE 'SURFACE_CLOSE|surface-close|probe-derive|risk_probes|pair_trigger\.reasons|finish-gate|resolve-stop-hook|durability-enforce|Execution phases|resolve-bootstrap' config/skills .agents/skills bin
- ! grep -rn 'devlyn:resolve' config/skills .agents/skills CLAUDE.md AGENTS.md package.json scripts/lint-skills.sh --include='*' | grep -v 'legacy'   # only DEPRECATED_DIRS in bin/devlyn.js and README legacy-map rows may remain
- ! grep -rniE 'token budget|max_tokens|solo-headroom|solo_claude|S2-S6' config/skills/devlyn:intent
- test $(cat config/skills/devlyn:intent/SKILL.md config/skills/devlyn:intent/references/*.md | wc -c) -le 40000 && test $(wc -c < config/skills/devlyn:intent/SKILL.md) -le 16000
- npm pack --dry-run --json | python3 -c "import json,sys; f=[x['path'] for x in json.load(sys.stdin)[0]['files']]; assert any('devlyn:intent/SKILL.md' in p for p in f); assert not any('devlyn:resolve' in p or 'finish-gate' in p or 'resolve-stop-hook' in p for p in f)"
- Installer migration (temp dir): git init; mkdir -p .claude/skills/devlyn:resolve; write .claude/settings.json with the legacy Stop hook command python3 "$CLAUDE_PROJECT_DIR/.claude/skills/_shared/resolve-stop-hook.py" plus one unrelated user Stop hook; run node <repo>/bin/devlyn.js -y with HOME set to a temp dir → .claude/skills/devlyn:intent/SKILL.md exists, .claude/skills/devlyn:resolve absent, legacy hook absent, user hook present, .claude/skills/_shared/resolve-stop-hook.py absent
- task-complete.py self-test case: complete without --mode and without devlyn.completionMode → PR created/reused, no 'gh pr merge --auto' invocation recorded
- git diff --check   # exit 0
- LIVE smoke 1 (disposable git repo, Claude Code owner claude-opus-5-5, OTHER = codex gpt-6-astra or grok-4.7): /devlyn:intent "<one-file bug fix with a failing test>" → trace has no separate PLAN/BUILD/CLEANUP/SURFACE/probe model calls; process-evidence manifests exist; primary + pair review ran; state phases.verify.verdict set by verify-merge-findings.py; archive_run moved artifacts; python3 .claude/skills/_shared/terminal-claim-check.py . exits 0; per-call usage recorded (UNKNOWN allowed, no budget)
- LIVE smoke 2: /devlyn:intent --spec docs/specs/<id>/spec.md with spec.expected.json and executor pinned via /devlyn:engines role worker {"engine":"codex","model":"gpt-6-sol"} → the edit is delegated through codex-monitored.sh with a .transport.json carrier; the owner does not re-implement; the final mechanical run includes the scope check
- LIVE smoke 3: seed a 0184-class defect (the output path may equal the input path) → a review finding is reproduced by an owner-authored failing check before repair, repaired, the final mechanical run is rerun, a fresh review runs, merged verdict PASS or honest NEEDS_WORK — never PASS with an open binding finding
- LIVE smoke 4: /devlyn:intent --verify-only <diff> --spec <path> → review-only verdict, no task-complete publication, terminal-claim-check CLEAN

## Dependencies

- User instruction 6: one design round with Astra (codex gpt-6-astra, read-only via codex-monitored.sh) on this packet's open questions BEFORE a fresh session implements it; the implementing session then executes this packet as one PR (push + PR only, no auto-merge).
- Research-vocabulary packet: owns solo-headroom/solo-ceiling/pair-evidence text in devlyn:ideate (SKILL.md:126; references/elicitation.md:44-55,124-129; from-spec-mode.md:49-58; project-mode.md:18-28; spec-template.md:121-122), the spec-verify-check --check/--check-expected solo-headroom validation, lint 6d/6f ideate pins, and codex-monitored.sh:64-75 + scripts/codex-shim (solo_claude arm guard). This PR deliberately leaves those in place.
- Benchmark-out-of-npm packet: owns benchmark scripts that call helpers this PR deletes or changes — state-phase-write (benchmark/ceiling/probes/sc-format-0076/validate-*.py, benchmark/ceiling/scripts/plan-dispatch-oracle.py), resolve-stop-hook (benchmark/layer-lift/run-lift-panel.py, benchmark/ceiling/probes/c1-product-wiring/run-pk-probe.py, benchmark/ceiling/scripts/run-ceiling-arm.sh, test-ceiling-harness.sh), finish-gate (benchmark/probes/scripts/check-compliance-cell.py), archive_run (benchmark/auto-resolve/scripts/iter-0033c-*), pair-plan-schema (pair-plan-*.py, oracle-test-fidelity.py), phase-prompt-render, judge-role-evidence (benchmark/probes/judge-quality) — plus lint 10d1, 10e, 13, 14, 15, the collector-contract call at scripts/lint-skills.sh:539-545, bin/devlyn.js:1025,1263 and package.json benchmark files. Those scripts break once this PR lands unless the benchmark packet freezes or removes them.
- Models/roles packet (user decision 3): adapter effort declarations for claude-opus-5-5 / claude-sonnet-5 / gpt-6-astra / gpt-6-sol / grok-4.7 (e.g. config/skills/_shared/adapters/claude.md <!-- devlyn-effort … claude-fable-5-1 … --> line); not changed here.
- Standards-skills frontmatter packet and installer-env packet (CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING, bin/devlyn.js:932-935) touch the same files (root-cause-analysis, code-health-standards, ui-implementation-standards, bin/devlyn.js). Agree on a landing order; recommend this PR first because it is the largest and moves shared paths, with the others rebasing.
- Queue/ideate consolidation into a single intent entry (0201-harness-transformation-plan.md:169-172 'reuse ideate alignment') is NOT in this packet; queue and ideate only get their references retargeted here.

## Open questions

- Review selection: keep resolve's non-bypassable review with dual-judge default-when-available (NORTH-STAR.md:269,271 user-approved exception; this packet's recommendation) or adopt 0204 owner.md:21-26 owner-selected review ('choose review for concrete interactions … record why local checks suffice')? Evidence that could move the user: 0184-review-repair-comparison.md:106-109 (OTHER-model review did not repair more than fresh same-model review) and 0197 (no fresh-context advantage). This is a user decision, not an implementer's.
- Where the surviving state writes live: this packet recommends shrinking state-phase-write.py to {--freeze-roles, plan spawn/complete (pre-edit scope binding), verify spawn/complete (review round)} as the single writer (0113 smoke-3 hand-edit lesson). The alternative distributes them into bootstrap / spec-verify-check / verify-merge. Astra should confirm one; distributing creates more write sites.
- Halts before review (implement-empty, build-env-underprovisioned, required-tools-unavailable, max-rounds, engine unavailable): record them as 'verify spawn + complete BLOCKED' (recommended; terminal-claim-check sees CLEAN/BLOCKED) or leave the state without a verdict (INCOMPLETE)? Either is non-success; the difference is queue labeling ([F] BLOCKED:<reason> vs FAILED-INCOMPLETE).
- Remove --risk-probes entirely (recommended; M5) or keep it as an explicit opt-in, given the benchmark-only lift at NORTH-STAR.md:273?
- /devlyn:resolve at the version boundary: hard removal with an installer purge + README migration (recommended; the user said full replacement) versus a one-version thin alias that prints the mapping (0201:174-177 allows either, but 'avoid permanently keeping two implementations').
- Delivery default: flip to 'pr' and keep 'auto' as an explicit opt-in via devlyn.completionMode/--mode (recommended; existing explicit configs keep working), or delete auto-merge support entirely?
- --max-rounds default: keep 4 (current bootstrap default, resolve-bootstrap.py:165) or align with the 0204/0205 two-review cap? This is a termination bound, not a token budget.
- Delegated Codex executor evidence: transport carrier + raw output only (recommended; D14 deletes the phase-owned invocation receipts, whose state consumer disappears) or keep DEVLYN_INVOCATION_* receipts for model/sandbox attestation (0112 R4)?
- Grok as pair reviewer: read-only static review with no anchor command (recommended; reviewers never execute and the owner reproduces). Its quality without anchor execution is unmeasured (adapters/grok.md 'not emission-certified').
- Rename resolve-bootstrap.py → intent-bootstrap.py in this PR (recommended while its callers are being edited anyway) or keep the file name to reduce churn?
- phase-prompt-render.py: wire it for review-prompt assembly per 0201-harness-transformation-plan.md:65 (recommended) or delete it as a product orphan (only benchmark/ceiling/scripts/plan-dispatch-oracle.py calls it today)?

## Verifier corrections (authoritative over the body)

- **CORRECTED** — The SKILL.md citations for D1/D3/D5/D11/D13, the M/K records and the state-schema.md citations are accurate
  - Nearly all match. One exception: D9 cites state-schema.md:100 for final-report binding, but that line is PLAN output_sha256. Final-report text is at :97, :118 and :130-138.
- **CORRECTED** — state-phase-write.py: non-test ~2,260 lines, self-test from :2260; function locations 150-196/198-222/261-409/891-934/937/1291-1560/1446/1563/1594/1668/2074-2140
  - The function locations are right. But main() at :5418-5661 is non-test code placed after the self-test, and final_report_self_test starts at :2157. The non-test code is therefore ~2,400 lines.
- **CORRECTED** — D14: after deleting receipts, bypass/sandbox rejection stays in codex-monitored.sh:83-93 and the transport carrier suffices
  - codex-monitored.sh:84-95 only rejects bypass flags and danger-full-access. Deleting start_receipt also deletes two iter0112 guards. First, the R5 mechanical refusal 'capability-denied phase/round cannot launch another Codex invocation' (invocation-receipt.py:236-253, spec iter0112 :83-88). Second, the R4 attestation of requested model and network. dispatch_codex/prepare_transport (:128-215, :1136-1172) check neither. K13's no-widened-retry guarantee then has no mechanical home, and the open question on receipts names only R4.
- **CORRECTED** — D16: the grok anchor lives at adapters/grok.md:69-101 (docs item says :56-101)
  - The anchor-guard wiring also sits at grok.md:27-30 (hook JSON in config), :35 (DEVLYN_PROBE_ANCHOR), :43-45 (--tools run_terminal_cmd, --allow Bash(anchor)) and :51-53 (seeding hooks/anchor-guard.json). All of it must go with grok-anchor-guard.py.
- **CORRECTED** — D17: only lint Check 13 and benchmark scripts read pair-plan-schema.md
  - Check 13 (lint :4107-4155) never reads it. The references are lint critical_path_files at :103 (mirror parity) and docstring/comment mentions in pair-plan-idgen.py:20, pair-plan-lint.py:4, :19, :235 and oracle-test-fidelity.py:30. Deleting it breaks nothing at runtime.
- **CORRECTED** — D1 tests: delete lint Check 6e (1495-1508)
  - 6e is 1495-1504. Lines 1505-1508 are Check 8's header comment.
- **CORRECTED** — A spec.expected.json that still declares required_risk_probe_requirements fails --check-expected with 'unsupported field'
  - The rejection text is 'unknown top-level key(s): …' (spec-verify-check.py:773-775). Removing the field also means deleting the EXPECTED_TOP_LEVEL_KEYS entry at :367, validation at :805-822 and resolution at :989-1089, beyond the :703-710/:1140-1170/:5175-5200 cited.
- **CORRECTED** — verify-merge-findings.py: delete :529-1106 and keep only the verdict core
  - That range includes verify_state_contract_violation (:692-777). Its checks for missing/malformed state, a missing primary engine and goal_path/goal_sha256 persistence on generated runs (:692-751) serve K25/R2 and should stay. Only the surface_close branch (:752-776) is SURFACE-specific.
- **CORRECTED** — archive_run.py 957→~800 needs only PER_RUN_PATTERNS and docstring edits
  - Completion is keyed on phases.final_report, which schema 4.0 deletes, in three places: is_completed (:173-192), the archive_plan final-report binding (:406-420) and prune (:498). Unless is_completed moves to phases.verify, prune never removes new runs, and the bootstrap's unfinished-run refusal (resolve-bootstrap.py:213) misclassifies them. Self-tests at :533-559, :655 and :871-885 also change.
- **CORRECTED** — task-complete.py pipeline_acceptance: keep 'declared process-evidence validation' unchanged
  - task-complete.py:271 and :281-284 match carriers on (phases.get(phase) or {}).get('round') for implement/build_gate/verify. Once phases.implement/build_gate are deleted these lookups return None, so they must use the same rounds.global rule proposed for process-evidence phase_round. :175 default 'auto' and :640-676 --auto merge are confirmed.
- **CORRECTED** — process-evidence.py 926→~930: only phase_round changes
  - mechanical_evidence_required also reads .devlyn/risk-probes.jsonl (:237-238), and verify-merge calls it through :150. Self-test fixtures at :676, :757, :788 and :832 build phases.implement/build_gate rounds and need updating.
- **CORRECTED** — role-config.py stays unchanged
  - observations() at role-config.py:218-230 reads phases.implement/cleanup model_effective and invocation_receipt. Schema 4.0 makes it dead code, an orphan this change creates. Self-test :380-386 is affected.
- **CORRECTED** — engine-doctor.sh stays unchanged; codex-config.md edits are :25, :35-58, :79-81
  - engine-doctor.sh:101 prints 'risk-probe escalation …' and codex-config.md:71 says 'pair/risk-probe VERIFY'. Both are stale after risk probes are removed. The acceptance grep pattern 'risk_probes' (underscore) catches neither.
- **CORRECTED** — .github/workflows/portability.yml:44 runs resolve-bootstrap.py --self-test
  - The command is at :46. Also missed: :190-193 (the Windows native install asserts the 'devlynresolve' dir and 'name: devlyn:resolve') and :198-199 (bootstrap self-test path on the installed package).
- **CORRECTED** — The resolve-bootstrap self-test only needs flag-matrix updates (:926-1380, :1054-1100)
  - resolve-bootstrap.py:1030-1034 finds the sibling 'devlyn:resolve'/'devlynresolve' skill dir, reads references/state-schema.md and asserts '"version": "3.0"' plus every PHASE_NAMES entry. Deleting state-schema.md and the resolve dir breaks it on POSIX and in Windows CI.
- **CORRECTED** — bin/devlyn.js citations (:18, :134-181, :250, :663, :725, :858, :896-923, :925, :932-935; cleanManagedSkillDirs :474-491; installSkillsForCLI :664-715)
  - The main line numbers match. Function spans are actually cleanManagedSkillDirs :481-495 and installSkillsForCLI :667-702. Missed :249 (comment 'pair/risk-probe routes fail closed').
- **CORRECTED** — devlyn:queue references at :24, :34-36, :37, :41
  - Also :3: the frontmatter description ends with 'spec → /devlyn:resolve → verified done'.
- **CORRECTED** — task-completion.md edits at :68-78 and :95-106; outer-loop.md :3
  - Also task-completion.md:4 ('finish-gate/archive authority', which the acceptance grep catches), :66 and :80 ('full resolve'), plus outer-loop.md:21 ('Bootstrap and resolve never make…'). There is no CHANGELOG in the repo; the packet's 'README/CHANGELOG' announcement has only a README target.
- **REFUTED** — Leaving lint 10d1/10e/13/14/15 to the benchmark packet is compatible with 'bash scripts/lint-skills.sh exits 0' in this PR
  - Check 10e at lint-skills.sh:2830-2877 runpy-loads verify-merge-findings.py and reads KNOWN_PAIR_TRIGGER_REASONS, which this PR deletes (verify-merge :52). Lint fails unless 10e is edited here or the benchmark packet lands first. Check 6c also replays real judge captures through read_findings/write_outputs (benchmark/ceiling/probes/r-weld-0082/test-collector-contract.py:81-89), which this PR rewrites.
- **CORRECTED** — test-windows-portability receipt cleanup: drop :1936-1941 and the finish-gate fixture :1957
  - worker() at :1855-1887 sets all DEVLYN_INVOCATION_* variables. The tests at :1889-1929 (tampering, competing, snapshot) are receipt-only, and :1938-1972 builds phases.implement.invocation_receipt plus a final_report binding. The whole block needs rewriting, not two line ranges. :237-270 also asserts CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING (:241-261), which overlaps the installer-env packet.
- **CORRECTED** — M1/K13 evidence: iter0112 spec.md:36-37 (plan binding) and :38-40, :83-88 (capability denial)
  - :36-37 is the duplicate-key counterexample (R2). Plan widening is counterexample 5 at :41-42, with R3 at :70-74. :38-40 is session provenance (R4). Capability denial is R5 at :83-88.
- **CORRECTED** — D4 deletes the classifier (free-form-mode.md:7-71) while K10/M7 keep the zero-scope halt (:62-63)
  - The zero-signal halt is defined by classifier signal file_scope_signals == 0 (free-form-mode.md:12, :55, :63). The packet must state the surviving zero-scope rule on its own, or K10 has no trigger.
- **CORRECTED** — The intent kernel is adapted from 0204 owner.md:8-48 and contains no budget
  - owner.md:6 ('total budget') and :33-34 ('Stop at the supplied budget … silently extending it') must be dropped to honor user decision 2. The acceptance grep 'token budget|max_tokens' would not catch 'supplied budget'.
- **CORRECTED** — Missing dependencies list is complete
  - Missing are external consumers of the skill name and state archives: the devlynd ResolveAdapter launches '/devlyn:resolve --goal-file' (SKILL.md:65), and devlyn-os reads run archives (crates/devlyn-runtime/src/resolve.rs, work_monitor.rs, cited in docs/specs/devlyn-history-lifecycle/spec.md:53). Renaming the skill and the schema-4.0 phase changes break them unless coordinated.

## Missed references found by the verifier

- config/skills/_shared/archive_run.py:173-192 (is_completed keys on phases.final_report), :406-420 (final-report binding in archive_plan), :498 (prune), self-tests :533-559, :655, :871-885
- config/skills/_shared/resolve-bootstrap.py:1030-1034 (self-test reads devlyn:resolve/references/state-schema.md and asserts v3.0 + PHASE_NAMES); also :213 prior-run completion via archive is_completed
- config/skills/_shared/task-complete.py:271, :281-284 (process-evidence carrier round lookup via phases.<implement|build_gate>.round); :5 docstring 'devlyn:resolve/references/task-completion.md'
- config/skills/_shared/process-evidence.py:237-238 (risk-probes.jsonl in mechanical_evidence_required); self-test fixtures :676, :757, :788, :832
- config/skills/_shared/role-config.py:218-230 observations() reads phases.implement/cleanup + invocation_receipt; self-test :380-386
- config/skills/_shared/invocation-receipt.py:236-253 capability-denied relaunch refusal (iter0112 R5), lost with start_receipt under D14
- config/skills/_shared/verify-merge-findings.py:692-751 verify_state_contract_violation guards (keep), inside the proposed :529-1106 deletion
- config/skills/_shared/spec-verify-check.py:769 and :5323 ('/devlyn:resolve --verify-only …' user-visible message); :1745-1759 authorized_surface_findings docstring ('BUILD_GATE-only … Not re-run at VERIFY MECHANICAL'); :367, :805-822, :989-1089 required_risk_probe_requirements handling
- config/skills/_shared/engine-doctor.sh:101 (risk-probe escalation text)
- config/skills/_shared/codex-config.md:71 ('pair/risk-probe VERIFY')
- config/skills/_shared/adapters/grok.md:27-30, :35, :43-45, :51-53 (anchor-guard hook config, DEVLYN_PROBE_ANCHOR, run_terminal_cmd/--allow), beyond :56/:69-101
- config/skills/devlyn:queue/SKILL.md:3 (description '→ /devlyn:resolve →')
- config/skills/devlyn:resolve/references/task-completion.md:4 ('finish-gate/archive authority'), :66, :80; references/outer-loop.md:21
- config/templates/prompt-templates.md:26, :64 (/devlyn:resolve; installed to .claude/templates via copyRecursive at bin/devlyn.js:805)
- bin/devlyn.js:249 (comment 'pair/risk-probe routes fail closed')
- .github/workflows/portability.yml:46 (not :44), :190-193 (Windows install asserts devlynresolve + 'name: devlyn:resolve'), :198-199 (bootstrap self-test path)
- scripts/lint-skills.sh:2830-2877 (Check 10e runpy needs verify-merge KNOWN_PAIR_TRIGGER_REASONS, deleted by this PR); :4157 (Check 14 comment containing '/devlyn:resolve', which fails acceptance #9); :510 (6b1 PHASES pin must stay consistent); :521-528 (6b2 receipt pins incl. 'SCHEMA_VERSION = "2.0"', 'DEVLYN_INVOCATION_RECEIPT')
- scripts/test-windows-portability.py:1855-1929 (receipt-only worker helper and three tests) in addition to :1936-1972; :241-261 overlaps installer-env packet
- scripts/test-owner-phases.py:139-180 (durability-enforce cases with cleanup origin)
- docs/specs/devlyn-history-lifecycle/spec.expected.json:9, :19 and spec.md:24-25, :30, :66-67, :86-88 (planned spec whose verification commands and authorized surface name resolve-bootstrap.py and devlyn:resolve paths; broken by the rename)
- autoresearch/experiments/0204/owner.md:6, :33-34 (budget language to drop when adapting the kernel prose)
- External (cross-repo): devlynd ResolveAdapter invoking '/devlyn:resolve --goal-file' (SKILL.md:65) and devlyn-os crates/devlyn-runtime/src/resolve.rs + work_monitor.rs reading .devlyn/runs/rs-* state (docs/specs/devlyn-history-lifecycle/spec.md:53)

## Acceptance checks the verifier could not run as written

- Acceptance #8 (! grep … 'resolve-stop-hook' … bin): the required installer migration in bin/devlyn.js must contain the literal legacy command '…/resolve-stop-hook.py' to find and remove the hook, so this check always fails. Exclude the migration line or match by another token.
- Acceptance #9 (! grep 'devlyn:resolve' … scripts/lint-skills.sh | grep -v legacy): lint-skills.sh:4157 (Check 14 comment, left to the benchmark packet) and the proposed 10c '/devlyn:resolve' guard both contain the literal, so the check fails unless those lines carry 'legacy' or are excluded.
- Acceptance #3 (bash scripts/lint-skills.sh exit 0): fails in this PR because Check 10e (lint :2830-2877) reads verify-merge KNOWN_PAIR_TRIGGER_REASONS, which this PR deletes. It passes only if 10e is edited here or the benchmark packet lands first, which contradicts 'leave 10e to the benchmark packet'.
- Acceptance #4 (self-test loop incl. intent-bootstrap): the existing bootstrap self-test (resolve-bootstrap.py:1030-1034) requires devlyn:resolve/references/state-schema.md. It stays red until that test is rewritten, which the packet does not name.
- Acceptance #6 / the portability workflow: the native Windows job (portability.yml:190-193, :198-199) hard-codes the devlynresolve dir and resolve-bootstrap.py path. It fails on the PR unless those lines change, and native Windows cannot be proven locally.
- LIVE smokes 1-4 need real model CLIs (claude-opus-5-5, codex gpt-6-astra/gpt-6-sol, grok-4.7) and a disposable repo. The implementing session can run them; this read-only verification could not.
- npm pack --dry-run --json writes npm logs/cache under ~/.npm. The implementer can run it; it was not run in this read-only verification.
- Installer-migration temp-dir check: node bin/devlyn.js -y with HOME overridden may also install detected Codex/omp targets into the temp HOME. It is runnable, but POSIX HOME override is needed (CI uses a preload for os.homedir).
