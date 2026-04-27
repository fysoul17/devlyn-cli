# HANDOFF — for the next session

**Outer goal lives in [`NORTH-STAR.md`](NORTH-STAR.md). Read that file FIRST — it is the project contract. This HANDOFF is the operating-context layer on top of it.**

**Read this second** in any new conversation continuing the AutoResearch loop. Smallest set of pointers that lets you pick up where 2026-04-27 (post-iter-0018 SHIP, post-iter-0016 5-fixture final readout, post-North-Star-refinement) left off.

---

## Current state

**Branch**: `benchmark/v3.6-ab-20260423-191315`. 15+ commits ahead of origin after iter-0018.5 commit.

**HEAD (committed at this HANDOFF rewrite)**: iter-0018.5 ← `5fd781a` iter-0018 ← `5d9ba0d` 5+1-principles surface ← `3bc6f45` North Star lock ← `27d1636` iter-0017 ← `775f761` HANDOFF rewrite ← `20f6f07` iter-0014 ← earlier chain. Working tree clean except untracked `.claude/` install dir.

iter-0007 verdict realized. iter-0008 REJECTED. **iter-0009 → iter-0014 + iter-0017 + iter-0018 + iter-0018.5 all SHIPPED**. iter-0016 5-fixture suite **completed** 2026-04-27T13:58Z (RUN_ID `20260427T121636Z-27d1636-iter-0016-verify`); judge fired and produced canonical scores; iter-0018 locked the readout into docs; iter-0018.5 closed the F5 surgical-scope and F9 spec-compliance failure modes at the BUILD/EVAL prompt level (text-only, no benchmark run).

**Next iteration QUEUE** (post-iter-0018.5, rewritten 2026-04-27 after Codex GPT-5.5 R0 split-iter pushback):

1. **iter-0019 — `L1-claude` smoke arm + comparison schema + `CODEX_BLOCKED` blocker shim** (next up — paid). Per Codex R0 Q1 (B over A): solo_claude arm cannot rely on `--engine claude` flag alone (iter-0008 proved prompt-only engine constraints are not enough). `CODEX_BLOCKED=1` env enforced inside both `scripts/codex-shim/codex` and `_shared/codex-monitored.sh` (fail-fast non-zero exit). solo_claude arm stages a blocker shim (codex on PATH for the arm refuses to run). Per Codex R0 Q2: smoke fixtures = **F1 + F2 + F4 + F6 + F9** (5 fixtures × 3 arms = 15 runs, ~$25-40, ~2h) — F1 keeps fast-route timing sentinel, F6 added because constraint discipline is exactly where L1 might beat L0. Per Codex R0 Q3: F2 `metadata.timeout` 1200→1500s (match F5/F6 budget; do not jump to 1800 — if 1500 still TO, treat the unmeasured inter-phase gap as the bug). Per Codex R0 Q6: real 3-arm schema in `judge.sh` + `compile-report.py` — `scores_by_arm`, `margins.{solo_over_bare, variant_over_bare, variant_over_solo}`, wall_ratio fields generalized to `L1_over_L0` / `L2_over_L1` / `L2_over_L0`. Same judge prompt scores all three arms (no separately-calibrated judge calls). **`L1-codex` deferred** — Claude is the auto-resolve orchestrator, no non-Claude orchestrator path exists yet (Codex R3 hard pushback). No pair-policy changes in this iter.
2. **iter-0020 — Pair-vs-solo policy formalization + tool-vs-deliberation attribution**. Per-phase decision-mode mapping per `NORTH-STAR.md`. Adds wall-time abort + `coverage.json` checklist-coverage artifact (every checklist ID with `pass/fail/na` + evidence path + touched-file scope, per Codex R3 Q4). **Critical instrumentation**: separate measurement of tool/phase lift (browser_validate, build_gate, security-review native firings) vs model-deliberation lift (second-model EVAL/CRITIC/JUDGE producing different conclusions). F4 may be tool-attributed not pair-attributed; F5/F9 excluded from this iter's attribution data per iter-0018 verdicts. After iter-0020 lands, run a full 9-fixture L0/L1/L2 suite to obtain canonical L2-vs-L1 numbers (this is where the 9-fixture run lives, not iter-0019).
3. **iter-0021 — Dual-judge permanent (`pair_consensus` for JUDGE phase)**. Resolves "GPT-only judge is a strategic liability" (Codex R1). Lands after iter-0020 because iter-0020 establishes pair vocabulary first.
4. **iter-0022 — Cost retune** (only if iter-0020 short-circuits + iter-0019 data show wall ratio still over budget after pair gates active). Otherwise close as "not needed."
5. Old queue items (iter-0015 shim defer, stream-json, F9 timeout adjustment, N=1 ship-gate floor, F6 chronic slowness, stuck-execution abort) renumber/recycle as the queue rotates.

**Codex R3 explicit warning**: do NOT bundle judge-mechanics changes + L1 arm + pair policy in the same iter — attribution becomes muddy. Sequence above keeps measurement and behavior changes separate.

**Cost estimate iter-0019 → 0021**: ~4-5 hours wall + 2-3 paid runs (~$30-60 total). iter-0019 paid (4-fixture × 3-arm smoke, ~$20-30); iter-0020 includes a full 9-fixture L0/L1/L2 paid run (~$30-50); iter-0021 reuses iter-0020's data for a re-judge sidecar (no new paid arm runs).

**Cost estimate iter-0016 → 0021**: ~3-4 hours wall + 2-3 paid suite runs ($30-60 total) before release-decision data lands.

---

## iter-0016 final readout (5-fixture partial — F1/F3/F7/F8 deferred to iter-0019)

RUN_ID `20260427T121636Z-27d1636-iter-0016-verify`. Completed 2026-04-27T13:58Z. Results dir `benchmark/auto-resolve/results/20260427T121636Z-27d1636-iter-0016-verify/`. Suite ran 5 of 9 fixtures (F2/F4/F5/F6/F9) per scope decision; F1/F3/F7/F8 deferred to iter-0019's L0+L1+L2 9-fixture run.

### Headline numbers

| Fixture | V score | B score | Margin | V wall | B wall | Wall ratio | Notes |
|---|---|---|---|---|---|---|---|
| F2 | 95 | 78 | **+17** | 1201s **TO** | 156s | 7.7× | Bare DQ silent-catch. Variant CRITIC killed at watchdog but quality high. |
| F4 | 99 | 78 | **+21** | 1012s | 177s | 5.7× | Bare missed italic CSS, added out-of-scope test-results file. browser=true. |
| F5 | 95 | 96 | **−1** | 770s | 45s | **17×** | Both spec=25/constraint=25/quality=21. Variant lost on scope=24 vs bare=25 (variant added `completed=` field to roadmap frontmatter). |
| F6 | 97 | 87 | +10 | 876s | 82s | 10.7× | Bare rethrows non-ENOENT, breaks createReadStream constraint. |
| F9 | 83 | 72 | +11 | 1393s | 87s | 16.0× | **Both arms verify=0.4, spec=16/13** — wrong `Error:` prefix, wrong exit 2, wrong JSON top-level shape, unranked authors. Bare DQ silent-catch. |

**Suite avg variant 93.8 / bare 82.2 / margin +11.6** (above the +8 NORTH-STAR preferred). 0 hard-floor violations. **SHIP-GATE FAIL** — only 4/5 fixtures ≥ +5 against absolute 7/9 floor (5-fixture run cannot pass a 7-of-9 absolute gate).

### Honest claim boundary (Codex R3 + R4 lock language)

- **L2 vs L0 (5-fixture partial)**: PASS on quality margin (+11.6 > +8 preferred), 0 hard-floor violations. FAIL on volume rule (5 fixtures only).
- **L2 vs L1**: **UNKNOWN**. L1 arm does not exist yet. iter-0019 must land before any L2-vs-L1 claim.
- **Release readiness**: NOT IMPLIED by these numbers. L2-vs-L1 compression risk (Codex R4): if L1 lands at, say, +9 vs L0, L2's effective lift over L1 is only +2.6 — below the +5 floor for L2 vs L1 in NORTH-STAR.md operational test #6. We do not know yet which side of that floor we are on.
- **Cross-vendor**: not measured. Per NORTH-STAR.md operational test #11, model-agnostic axis is de-prioritized.

### Per-fixture diagnoses (Codex R4 verdicts)

- **F2** — variant +17 despite watchdog timeout. CRITIC killed mid-phase (state writes confirmed: build/build_gate/evaluate populated, critic phase started but verdict=-/duration=0). F2 timeout=1200s too tight for full 4-phase pipeline + inter-phase gaps. Bump to 1500-1800s candidate for iter-0019 fixture metadata.
- **F4** — variant +21, the largest L2 lift. **Plausibly tool-attached** (browser_validate + native security-review on browser=true) per Codex R3, not pair-deliberation-attached. iter-0020 must instrument tool-vs-deliberation attribution before claiming pair lift here.
- **F5** — variant −1 on scope. Codex R4 verdict: "**root cause is surgical-change failure, not pairing is inherently waste**. The waste signal is real (17× wall for no quality gain), but the actionable fix is BUILD policy: stricter scope boundary, no opportunistic metadata edits, audit must explicitly reject unrelated file/frontmatter/status changes." → iter-0019 BUILD prompt fold-in.
- **F6** — variant +10, bare hits two CRITICAL findings (non-ENOENT rethrow, createReadStream constraint violation). Genuine pair lift on constraint discipline.
- **F9** — both arms verify=0.4 spec=16/13. Same output contract failure across L0 and L2: missing `Error:` prefix, wrong exit 2, wrong JSON shape, unranked authors. Codex R4 verdict: "measurement/report integrity adjacent because both arms failed the same output contract. **Do not use F9 for pair-policy conclusions until fixed.**" → iter-0018 spec/pipeline diagnosis required.

### What iter-0014/0017 protocol confirmed (positive)

- iter-0014 state-writes-per-phase: F2 variant `phases.{build, build_gate, evaluate, critic}` populated even on watchdog kill. Pre-iter-0014 would have shown only `evaluate`. Causality attribution to CRITIC was possible because of this.
- iter-0012 `WATCHDOG_FIRED` sentinel: F2 variant `result.json.timed_out=true`, `invoke_exit=124`.
- iter-0017 auto-mirror: `[suite] mirrored 26 committed skill(s)` at suite startup.
- F4 variant `phases.{browser_validate, build, build_gate, evaluate}` — browser_validate phase visible (not exercised in F1-only iter-0014 falsification gate).

### Open observability gap

F2 variant: 678s of inter-phase time unaccounted by per-phase `duration_ms` (sum of `build+build_gate+evaluate+critic` durations = 523s; arm wall = 1201s). Phase 1.4/1.5 routing not measured by current state-write protocol. iter-0019 or iter-0020 BUILD/EVAL prompt fold-in may close this; defer if not load-bearing.

## North Star refinement (2026-04-27, post-iter-0017)

User clarified the project goal in two passes during this session:

1. **3-layer performance contract**: L0 bare → L1 solo harness → L2 pair harness. Single-LLM users (Opus alone, GPT-5.5 alone) are first-class — they get L1, which must beat L0. Multi-LLM users get L2, which must beat L1. **De-prioritized**: cross-vendor "model-agnostic" axis (Qwen / Gemini / Gemma); not the North Star.
2. **Efficiency is first-class at every layer**: each layer must beat `previous-layer-best-of-N` where N is the wall-time ratio. "Pair is slower but more thoughtful" is rejected — if L2 takes 17× the wall-time of L0 at verify-tie, the user could have run bare-best-of-17 and likely gotten a better result.

Codex GPT-5.5 R1 + R2 review concurred with the L0 / L1 / L2 framing and contributed:

- Release gate numbers (suite avg margin ≥ +8 preferred / ≥ +5 floor; F9 ≥ +5; 7/9 fixtures ≥ +5; zero variant DQ/CRITICAL/HIGH/timeouts).
- Per-phase decision-mode taxonomy (`solo` / `pair_critic` / `pair_consensus`) and the table now in `NORTH-STAR.md`.
- Pushback on EVAL = unconditional pair (would recreate F5/F6 waste): made it **gated solo → escalate to pair_critic only on signals**.
- Pushback on full profile-neutral runtime abstraction (`engine-roles.json` + dispatcher): **overengineering** since model-agnostic is no longer the North Star. Keep policy in text only; provider names stay inline in SKILL.md PHASE blocks.
- Iteration-loop pair vs auto-resolve pair: **same vocabulary, different thresholds** (iter-loop tolerates more pair because cost is amortized over harness improvements; auto-resolve must be aggressively gated because every pair call is paid by the user on every run).

`PRINCIPLES.md` gained a sixth principle, "Layer-cost-justified," that operationalizes the efficiency contract. Iteration files now must enumerate principles 1–6.

## What was just shipped (iter-0017)

Full data in `iterations/0017-run-suite-auto-mirror.md`.

Single-file diff, +33 lines, in `benchmark/auto-resolve/scripts/run-suite.sh`.
Adds an auto-mirror block right after the run banner that replicates
`bin/devlyn.js`'s `cleanManagedSkillDirs` + `copyRecursive` semantics for the
skills tree only — no `CLAUDE.md` copy, no `.gitignore` mutation, no
`settings.json` writes, no agent-pack install. Per-skill staging dir +
atomic `mv` keeps Ctrl-C from leaving a managed skill missing. UNSHIPPED list
inline (4 entries; comment points at `bin/devlyn.js:299`). Skipped only in
`--judge-only`; runs in `--dry-run` so suite-setup verification covers the
mirror path.

Falsified locally: marker injection + drift simulation + dry-run produced
`[suite] mirrored 26 committed skill(s)` stamp; marker propagated; drift
removed; user-installed skills preserved (verified with synthetic
`.claude/skills/fake-user-skill/`); UNSHIPPED workspace dirs absent in
`.claude/skills/`. Lint 10/10. Zero model spend.

Codex GPT-5.5 R0 (84s, 41k tokens) verdict: M2 (inline shell) over M1
(`bin/devlyn.js -y` — too broad) and M3 (rsync — macOS variance). All R0
recommendations adopted verbatim.

## What was shipped before that (iter-0014)

Full data in `iterations/0014-state-writes-per-phase.md`.

6-file diff, +138/-21, no new files, no new abstractions. Two bugs closed in one iter, both surfaced from iter-0013's F1 successful run:

1. **State-writes-per-phase contract drift.** `pipeline-state.md:165-171` requires per-phase `phases.<name>.{started_at, round, triggered_by}` (orchestrator) at start and `{verdict, completed_at, duration_ms, artifacts}` (phase agent) at end. Pre iter-0014 F1 runs populated only `phases.evaluate`.
2. **Archive script path bug** (Codex iter-0014 R0 finding). SKILL.md ran `python3 scripts/{archive_run.py, terminal_verdict.py}` from work_dir, but those scripts live at `.claude/skills/devlyn:auto-resolve/scripts/`. Silent failure → artifacts piled in `.devlyn/`, never moved to `.devlyn/runs/<run_id>/`.

Edits:

- `config/skills/devlyn:auto-resolve/SKILL.md` — new `<state_write_protocol>` block; per-phase one-line reminders for PHASE 1/1.4/1.5/2/3/4; PHASE 5 detailed write directive; fixed script paths to `.claude/skills/devlyn:auto-resolve/scripts/`.
- `references/phases/phase-1-build.md` / `phase-2-evaluate.md` / `phase-3-critic.md` — explicit final-state-json write line listing all required fields.
- `autoresearch/iterations/0014-state-writes-per-phase.md` (new).
- `autoresearch/HANDOFF.md` (this file, updated again now).

Falsification gate (RUN_ID `iter0014-verify-20260427T092859Z`):

| Phase | verdict | started_at | completed_at | duration_ms | engine | artifacts |
|---|---|---|---|---|---|---|
| `build` | PASS | 2026-04-27T09:29:50Z | 2026-04-27T09:33:22Z | 212000 | codex | `{}` |
| `build_gate` | PASS | 2026-04-27T09:34:30Z | 2026-04-27T09:34:35Z | 5000 | bash | `{findings_file, log_file}` |
| `evaluate` | PASS | 2026-04-27T09:34:40Z | 2026-04-27T09:35:30Z | 50000 | claude | `{findings_file, log_file}` |
| `final_report` | PASS | 2026-04-27T09:35:45Z | 2026-04-27T09:35:50Z | 5000 | bash | `{}` |

elapsed=610s under 900s budget; verify_score=0.8; archive ran (`.devlyn/runs/ar-20260427T092945Z-f221066a9098/` populated).

---

## Decided next step — recommended

**Recommendation: full-suite verification run under iter-0014** (filed as iter-0016 below). Concrete pain check: confirm F2/F4/F5/F6/F9 also benefit from per-phase state writes + archive fix, and surface any CRITIC/DOCS observability gaps that the F1-only verify (fast route) didn't exercise. Cost: ~1 hour wall, ~$10-20 spend.

If user prefers not to spend on a suite run: pick from the queue below by current pain. Option A (shim distribution, iter-0015) stays deferred per Karpathy #2 unless production regression observed.

---

## Critical gotcha — sync gap (now self-healing)

**As of iter-0017, `run-suite.sh` auto-mirrors `config/skills/` → `.claude/skills/`** at the top of every invocation (skipped only in `--judge-only`). Manual mirror via `node bin/devlyn.js -y` is no longer required before benchmarks.

**Still useful before a commit / lint pass**:

```bash
diff -rq config/skills/ .claude/skills/ 2>&1 | grep -v "Only in"
```

Expected: silence (UNSHIPPED_SKILL_DIRS legitimately have `Only in config/skills/...` lines per `bin/devlyn.js:299` exclusion list). If non-empty, either run `bash benchmark/auto-resolve/scripts/run-suite.sh --dry-run F1` (cheapest sync) or `node bin/devlyn.js -y` (full installer).

iter-0014 specifically modified: `SKILL.md`, `phase-1-build.md`, `phase-2-evaluate.md`, `phase-3-critic.md`. Those four are mirror-parity-checked by lint Check 6. Lint enforces the equivalence at commit time even though run-suite handles it at run time.

---

## Cross-judge sidecar — iter-0006-full data still relevant

`benchmark/auto-resolve/results/20260426T034926Z-1ac7594-iter-0006-full/cross-judge-summary.json` has Opus 4.7 dual-judge data over the same sanitized prompts. Pearson(margins)=0.988, winner_agree=6/9, sign_agree=7/9. Mild self-judgment bias signal (~5.6pt — GPT-5.5 inflates variant scores relative to Opus). Permanent dual-judge in `judge.sh` queued as iter-0019.

---

## What is shipped vs queued (post iter-0014 SHIP)

### Shipped on this branch (chronological)

`DECISIONS.md` is canonical. Quick map:

- iter 0001 — skill scope-first + trivial-fast routing
- iter 0002 — F6/F7 spec annotation
- iter 0003 — process-group watchdog
- iter 0004 — outer claude -p MCP isolation
- iter 0005 REVERTED
- iter 0006 REVERTED (per iter-0007 verdict)
- iter 0007 — F6 isolation experiment, conclusive
- iter 0008 REJECTED (prompt-level contract empirically dead)
- iter 0009 SHIPPED — wrapper + PATH shim. F2 BUILD ran 399.9s through wrapper without watchdog kill; F6 +60-pt recovery.
- iter 0010 SHIPPED — production rollout of wrapper-form to ideate / preflight / team-resolve / team-review; lint Check 10 added; shim shipping deferred per Codex R1 ship-blocker.
- iter 0011 SHIPPED — Codex Option D: Check 10 evasion-shape close (pattern broadened to invocation-class `codex exec[[:space:]]+\S`) + priming-token scrub in shared docs. Falsification canary 6/6.
- iter 0012 SHIPPED — `run-fixture.sh` `timed_out` derivation switched to WATCHDOG_FIRED Bash sentinel (vs `elapsed >= timeout`).
- iter 0013 SHIPPED — F1 metadata.timeout 480→900s after Codex-corrected reframe and 465s clean discriminator.
- **iter 0014 SHIPPED** — state-writes-per-phase observability + archive script path. D4-lite design (universal block + per-phase reminders + prompt-body strengthening) per Codex R0; archive bug found via Codex grepping `archive_run.py`.
- **iter 0017 SHIPPED** — `run-suite.sh` auto-mirror `config/skills/ → .claude/skills/`. Codex GPT-5.5 R0 picked M2 (inline shell mirror) over M1 (`bin/devlyn.js -y`, too broad — touches CLAUDE.md, .gitignore, project + global settings, agent packs) and M3 (rsync, macOS variance). Per-skill staging dir + atomic `mv` for Ctrl-C safety. Falsified locally with marker injection + drift simulation + user-skill-preservation test; lint 10/10; zero model spend.
- **iter 0016 (5-fixture suite)** — F2/F4/F5/F6/F9 ran post iter-0014/0017; suite avg variant 93.8 / bare 82.2 / margin +11.6 / wall ratio 11.4×. SHIP-GATE FAIL (volume rule: 4/5 ≥ +5 against absolute 7/9 floor). 0 hard-floor violations. F2 +17 (variant TO at 1200s but quality high), F4 +21 (largest L2 lift, plausibly tool-attached), F5 −1 (variant added `completed=` to roadmap frontmatter — surgical-scope failure not pair waste), F6 +10 (genuine constraint lift), F9 +11 but both arms verify=0.4 spec=16/13 (pipeline-level spec-compliance failure, not pair vs solo). Final readout in `iter-0016` results + `iterations/0018-measurement-integrity.md`.
- **iter 0018 SHIPPED** — Measurement integrity + report-shape lock. Added `wall_ratio_variant_over_bare` per-row + `wall_ratio_variant_over_bare_avg` aggregate to `summary.json` and report.md. Locked iter-0016 final readout into HANDOFF.md + NORTH-STAR.md operational test #13 (L2-vs-L1 compression risk, "release not implied" honest-claim language). Classified F5 as surgical-scope failure (iter-0019 BUILD prompt fold-in) and F9 as pipeline spec-compliance failure (iter-0019/0020 BUILD/EVAL prompt fold-in). CLAUDE.md gained Codex companion pair-review section distinguishing iteration-loop pair from auto-resolve pair (same vocabulary, different thresholds). Diagnostic-only — zero paid runs, lint 10/10.
- **iter 0018.5 SHIPPED** — BUILD/EVAL prompt fold-ins for F5 (spec-frontmatter ban) + F9 (literal-verification rule + EVAL `correctness.{exit-code,spec-string,json-shape,format}-mismatch` + `scope.frontmatter-edit` rule_ids). 4 bullets total across `phase-1-build.md` + `phase-2-evaluate.md` `<quality_bar>` blocks. Codex R0 Q4/Q5/Q7 verdicts adopted verbatim; split from iter-0019 to keep attribution clean. Text-only — zero paid runs, lint 10/10. Behavior claim is iter-0019's job (F5 variant scope should return to 25, F9 variant spec should reach ≥22).

### Queued (next hypotheses, ordered, post iter-0017)

1. **iter-0015 — shim distribution to user installs** (long-deferred per Karpathy #2). Design fail-open shim + `devlyn doctor activate` (NOT npm post-install) + idempotent settings.json merge. Revisit when production regression observed.
2. **iter-0016 — full-suite verification under iter-0014/0017**. Run F2/F4/F5/F6/F9 and confirm state-write protocol + archive fix carry over. May surface CRITIC/DOCS phase observability gaps on `standard` route. Now safer post iter-0017 (auto-mirror closes one of the two stale-skill failure modes).
3. **iter-0018 — `claude -p --output-format stream-json`** for variant arm. Would make transcript flush incrementally and survive SIGTERM partial output. Optional; not pressing once F1 budget is right.
5. **iter-0019 — permanent dual-judge in judge.sh** (`memory/project_dual_judge_2026_04_26.md`).
6. **iter-0020 — silent-catch fixture spec**. F2 spec language allows BUILD output with `catch { return fallback }`; tighten.
7. **iter-0021 — F9 wall-time regression**. Both iter-0006 single-fixture F9 attempts took >30 min. Bump F9 metadata.timeout to 5400s.
8. **iter-0022 — single-fixture ship-gate hard-floor bug**. Ship-gate currently passes catastrophic regression on N=1 because 7/9 floor not applied at N=1.
9. **iter-0023 — F6 chronic slowness investigation**.
10. **iter-0024 — auto-resolve stuck-execution abort criteria** (skill guardrail G5).
11. **5-Why operationalization in CLAUDE.md** (codex round 2 Karpathy #1 expansion).
12. **DOCS Job 2 wider verification** (long-queued).
13. **Held-out fixture set** (don't build until 3+ fixtures improve with no intuitive mechanism).
14. **Adversarial-ask layer** (long-term).

### Deferred (user-direction, awaiting explicit user call)

- Multi-LLM orchestration modes (3 modes + extensibility) — `memory/project_orchestration_modes_2026_04_26.md`.
- Benchmark cross-mix arms — `memory/project_benchmark_cross_mix_2026_04_26.md`.

---

## How to resume cleanly in a new session

1. **Read `autoresearch/NORTH-STAR.md` first.** Outer goal + L0/L1/L2 contracts + per-phase decision-mode taxonomy. Ground truth.
2. **Read `autoresearch/HANDOFF.md` second** (this file). Operating context layered on top of the goal.
3. `cd /Users/aipalm/Documents/GitHub/devlyn-cli && git status && git log --oneline -8` — confirm branch state matches the HEAD chain above.
4. `diff -rq config/skills/ .claude/skills/ 2>&1 | grep -v "Only in"` — must be silent before any benchmark run (note: as of iter-0017 `run-suite.sh` self-heals at the start of every invocation, so this check is now belt-and-suspenders, not load-bearing).
5. `bash scripts/lint-skills.sh` — must pass all 10 checks before any commit.
6. **All Codex collaboration goes through the local CLI**, never MCP. User direction (memory: `feedback_codex_cross_check.md`). Pattern: `bash config/skills/_shared/codex-monitored.sh -C /Users/aipalm/Documents/GitHub/devlyn-cli -s read-only -c model_reasoning_effort=xhigh "<prompt>"`. Never pipe the wrapper output (`| tail`, `| head`, `| grep` without `--line-buffered`) — pipe-stdout is refused per iter-0009.
7. Reason independently first; consult Codex with rich evidence; never delegate the decision (`feedback_user_directions_vs_debate.md`).
8. **If iter-0016 background suite is still running** (PID 12825 alive, log `/tmp/iter-0016-logs/suite.log` growing): do NOT interrupt. iter-0018 is the diagnostic-only follow-up that consumes its results.

---

## Don't lose these decisions / lessons (cumulative)

1. **CLAUDE.md stays clean of conditional rules.** 5-Why is Karpathy #1 expansion, not a new top-level rule.
2. **RUBRIC.md does not change** during a benchmarking window.
3. **Don't build held-out fixtures yet.** Trigger: 3+ fixtures improve with no intuitive mechanism.
4. **Don't blanket-kill `codex-mcp-server` processes.** Iter 0003's narrow watchdog is the right scope.
5. **The four oracles are tools, not the loop.** The loop is iteration files + DECISIONS.md + benchmarks.
6. **`claude-debug.log` is metadata-only.** For "did codex run?", use `~/.codex/sessions/` + `pipeline.state.json`.
7. **Single-fixture falsification gate is necessary but not sufficient** for full-suite ship — but **single-fixture isolation IS sufficient for causality attribution** when comparing two HEADs (iter-0007 proved this).
8. **Don't pass `--accept-missing` to ship-gate when all 9 fixtures exist.**
9. **Self-judgment bias** is real (~5.6pt). Permanent dual-judge queued as iter-0019.
10. **Universal contract rules over-fit single failure modes.** iter-0006 banned a category to prevent a specific shape; the category is broader than the shape. Apply skill guardrails G1-G5 (`memory/project_skill_guardrails_2026_04_26.md`) before merging any contract change.
11. **Read your own data carefully.** Codex Round 16 caught a CSV column-order misread; iter-0014 R0 caught a wrong knock-on-bug claim by reading `archive_run.py` itself.
12. **User directions ≠ debate prompts.** When user says "we're going X direction," ask codex for best practice + improvements, NOT "should we?". Surface codex pushback transparently. (`feedback_user_directions_vs_debate.md`)
13. **`zsh -c source <snapshot>` overrides parent PATH.** Project-scope `$WORK_DIR/.claude/settings.json env.PATH` override is the only reliable way to inject PATH into Bash dispatches inside `claude -p`. (iter-0009.)
14. **`[ -p /dev/stdout ]` is the portable POSIX test for "stdout is a pipe."** Used in iter-0009 wrapper.
15. **Cross-model GAN earned its keep at every iter from iter-0009 onward.** Continue dual-model practice. iter-0014 R0 caught a separate archive bug I'd missed entirely.
16. **Static gate suffices when mechanism is unchanged** (iter-0010 lesson). Text-only changes that ride on a proven mechanism don't need a benchmark gate; lint check + canary is the right scope.
17. **Pattern-priming applies even to descriptive text** (iter-0010/0011 lesson). Phrases like "passes args through to `codex exec` verbatim" leak the token into orchestrator prior. Rephrase in prompt-facing files.
18. **Lint patterns must cover all syntactic shapes the orchestrator can emit** (iter-0010 R2 + iter-0011 lesson). Multi-line `codex exec \` had to be added; quoted/variable/literal shapes too. Bind the invocation *class*, not specific shapes.
19. **`set -u` traps are silent until they fire** (iter-0012 lesson). Pre-initialize every variable that downstream `export` references in the branch where it's introduced.
20. **References are docs; SKILL.md PHASE sections are scripts** (iter-0014 lesson). Contracts that live only in references get ignored at action time. Salience matters: contracts must surface where the orchestrator's attention is during execution.
21. **Prompt-body output contracts alone are not enough** (iter-0014 lesson). `build-gate.md` had explicit per-field contract and orchestrator still skipped the write empirically. Defense in depth: orchestrator validates after agent.
22. **Script paths must be relative to where they're invoked from** (iter-0014 lesson). SKILL.md ran `scripts/archive_run.py` but the orchestrator runs from work_dir; use `.claude/skills/<skill>/scripts/...` for portability.
23. **HANDOFF framings can decay** (iter-0013 lesson). Always re-read raw artifacts; never trust prior framings without verification.
24. **Change one variable per iter when measurement matters** (iter-0018.5 lesson). Codex R0 Q7 framing: bundling prompt edits + new arm + schema change makes attribution muddy. Split into prompt-only iter (text fix) + arm/schema iter (behavior fix) so any movement attributes cleanly. iter-0018.5 (prompt fold-ins) → iter-0019 (arm + schema) is the worked example.
25. **EVAL must execute, not just opine** (iter-0018.5 lesson). F9 in iter-0016 had spec=16 because EVAL inspected the diff but never ran the spec's `verification_commands`. Literal-match-by-execution is a different discipline; lives in EVAL `<quality_bar>` with four `rule_id`-anchored bullets (`correctness.{exit-code, spec-string, json-shape, format}-mismatch`).
26. **`quality_bar` is the right surface for cross-cutting BUILD/EVAL contracts** (iter-0018.5 lesson, builds on iter-0014 #20). Bullets there get re-read every phase invocation; rules buried in `references/findings-schema.md` reference docs may not be loaded at action time. When adding a new contract that the orchestrator must enforce, place it in `<quality_bar>` first; promote to a separate reference only if the contract grows beyond bullet-shape.
27. **Engine-routing is not the place for output-contract rules** (iter-0018.5 lesson, Codex R0 Q5). `_shared/engine-routing.md` controls *which engine* runs each phase; output contract (frontmatter ban, literal-match) is *what each engine does*. Different layers — do not conflate. Output contracts live in the phase prompt's `<quality_bar>`.
28. **Pair-policy claims need attribution between tool-lift and deliberation-lift** (iter-0018 / Codex R3 lesson). F4's +21 in iter-0016 is the largest L2 lift but plausibly tool-attached (browser_validate + native security-review fired on browser=true). Until iter-0020 instruments the two signals separately, "pair > solo" is unproven. iter-0019 / 0020 must keep this distinction live.

---

## Codex collaboration log (running)

- R1–R5 (iter 0005): inner-codex flag bundle work.
- R6: expand falsification gate F2 → F5 → F4 → F9 → full.
- R7: sync-gap fix = Option A.
- R8: routing-telemetry observability (later moot).
- R9: F4 score-94 borderline pass.
- R10: F9 #1 environmental, RERUN.
- R11: F9 #2 strict-fail by criteria.
- R12: harness-truth halt — RETRACTED in R13.
- R13: confirm retraction, run full-suite.
- R14: post-results — DEFER not REVERT, F6 isolation as iter-0007.
- R15: strategic check — fold iter-0008 wall-time into iter-0007, cut iter-0012 for now.
- R16: caught CSV column-order misread (F6 prior 0-files claim wrong; F4/F5 noise → "shared runtime/API failure").
- R17: post-isolation — REVERT confirmed; iter-0008 = narrow kill-shape ban.
- iter-0009 R1: hook → PATH shim swap. Wrapper streams full stdout (no `tail -200`).
- iter-0009 R2: `| tail -200` defeats wrapper streaming → wrapper must refuse pipe-stdout via `[ -p /dev/stdout ]`. Heartbeat to stderr (cleaner stdout = codex output). Mirror parity for `engine-routing.md`.
- iter-0010 R1: shim-shipping ship-blocker (hard-fails 127 without env wiring). Heartbeat doc bug. Drop shim-shipping; defer.
- iter-0010 R2: lint Check 10 multi-line blind spot caught before commit. Residual descriptive `codex exec` mentions to rephrase.
- iter-0011 R0: I proposed B → C → defer A (Karpathy #2). Codex flagged a real risk class (`codex exec "<prompt>"` evasion shape) and proposed Option D = cheap hardening (broaden Check 10 + scrub priming tokens). Adopted as iter-0011.
- iter-0012 R0: 5-line `timed_out` fix verdict. Caught (1) invariant misstatement (`elapsed=TIMEOUT-1` was already correct under `>=`); (2) `set -u` init-order trap requiring `WATCHDOG_FIRED=0` before `if DRY_RUN`; (3) don't couple to `INVOKE_EXIT==124`; (4) no new schema field; (5) leave SIGTERM grace alone; (6) `kill -0` race deferred.
- iter-0013 R0: F1 starvation reframe. Caught (1) my "0.6s away from natural exit" was over-asserted (SessionEnd hooks can be SIGTERM cleanup); (2) F1 didn't complete fast route; (3) one Bash dispatch took 268.5s. Recommendation: 900s discriminator first. Outcome A confirmed.
- iter-0014 R0: state-writes-per-phase + archive fix. Verdict: D4-lite (universal block + per-phase salience + prompt-body fixes). Pushback on knock-on bug claim — Codex read `archive_run.py` and showed moves are unconditional; verdict gates pruning only. Real cause: separate path bug. F1 verified post-fix.
- iter-0017 R0: auto-mirror config/skills → .claude/skills. Verdict: M2 inline shell (over M1 `bin/devlyn.js -y` too broad, M3 rsync too fragile). Per-skill staging + atomic mv for Ctrl-C safety. UNSHIPPED list inline + comment pointer.
- North Star R1 (84s, 41k tokens): release-gate numbers locked (suite avg ≥ +8 / ≥ +5, F9 ≥ +5, 7/9, zero DQ/CRITICAL/HIGH/timeouts). Per-phase decision-mode taxonomy (`solo` / `pair_critic` / `pair_consensus`). Iteration-loop pair vs auto-resolve pair = same vocabulary, different thresholds.
- North Star R2 (16k tokens): EVAL=gated solo not unconditional pair (would recreate F5/F6 waste). Profile-neutral abstraction = text-only, no runtime engine-swap dispatcher (overengineering since model-agnostic ≠ North Star).
- North Star R3 (97k tokens): re-ordered iter-0019 (L1-claude arm) ahead of iter-0020 (pair policy). L1-codex deferred (no non-Claude orchestrator path exists yet). F4 lift plausibly tool-attached (browser_validate) not pair-attached — pair > solo unproven. L2 release gate split from L1 (L1 must pass first; L2 vs L1 needs +5 on pair-eligible fixtures only).
- iter-0018 R0 (19k tokens, 27s): start iter-0018 on 5-fixture data; defer F1/F3/F7/F8 to iter-0019 paid run. F5 root cause = surgical-scope failure (BUILD added `completed=` to roadmap frontmatter beyond strict scope) not pair-deliberation waste. F9 = measurement-integrity adjacent (both arms failed same output contract — pipeline BUILD/EVAL prompt issue, not pair vs solo). L2-vs-L1 compression risk locked into NORTH-STAR.md test #13.
- iter-0019 R0 (terse, on iter-0018.5+0019 design): **B over A on solo_claude arm** — `CODEX_BLOCKED` env enforced in shim + monitored.sh, blocker shim staged on solo_claude arm; A (`--engine claude` flag alone) too trust-based, iter-0008 proved prompt-only engine constraints insufficient. **F1+F2+F4+F6+F9 fixture set** (added F6 for constraint-discipline coverage where L1 might beat L0, kept F1 as fast-route sentinel). **F2 timeout 1500s** not 1800 (if still TO, treat inter-phase gap as the bug). **Q4 wording fix**: my draft implied BUILD might do the status flip; Codex's wording correctly attributes the flip to DOCS only. **Q5 location**: BUILD `quality_bar` + EVAL `quality_bar`, not shared engine-routing.md (engine-routing is wrong layer; it controls which engine, not what engine does). **Q5 active enforcement**: my draft was passive ("must match the spec"); Codex pushed for "EVAL forced to execute the verification commands and produce findings" — adopted via four `rule_id`-anchored bullets. **Q6 schema risk**: `judge.sh` + `compile-report.py` are hard-coded variant/bare; iter-0019 must add real 3-arm schema (`scores_by_arm`, `margins.{solo_over_bare, variant_over_bare, variant_over_solo}`, wall ratios), and the same judge prompt must score all three arms (no separately-calibrated judge calls — would invalidate L2-vs-L1 derivation). **Q7 split**: iter-0018.5 (prompt-only) + iter-0019 (arm + schema) keep attribution clean. All Q1-Q7 verdicts adopted verbatim.

---

## Memory entries that matter (cumulative)

Stored in `~/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/memory/`:

- `feedback_codex_cross_check.md` — dual-model GAN pattern.
- `feedback_auto_resolve_autonomy.md` — hands-free contract.
- `feedback_user_directions_vs_debate.md` — user directions are decisions, surface codex pushback.
- `project_v3_*.md` — historical harness redesign series.
- `project_autoresearch_framework_2026_04_25.md` — framework genesis.
- `project_skill_sync_gap_2026_04_26.md` — sync-gap gotcha.
- `project_orchestration_modes_2026_04_26.md` — DEFERRED, user-direction.
- `project_benchmark_cross_mix_2026_04_26.md` — DEFERRED, user-direction.
- `project_dual_judge_2026_04_26.md` — DECIDED, A sidecar shipped, B queued as iter-0019.
- `project_skill_guardrails_2026_04_26.md` — G1-G5 design constraints from iter-0006/0007.
- `project_iter0009_shipped_2026_04_27.md` — wrapper + PATH shim ship details.
- `project_iter0010_shipped_2026_04_27.md` — production rollout + shim shipping deferred.
- `project_iter0011_shipped_2026_04_27.md` — Codex Option D: Check 10 evasion-shape close + priming-scrub.
- `project_iter0012_shipped_2026_04_27.md` — `timed_out` derivation switched to WATCHDOG_FIRED sentinel.
- `project_iter0013_shipped_2026_04_27.md` — F1 timeout discriminator: 480→900s; HANDOFF reframe corrected.
- `project_iter0014_shipped_2026_04_27.md` — state-writes-per-phase + archive script path.
