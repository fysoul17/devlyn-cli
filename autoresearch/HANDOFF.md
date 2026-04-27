# HANDOFF — for the next session

**Read this first** in any new conversation continuing the AutoResearch loop. Smallest set of pointers that lets you pick up where 2026-04-27 (post-iter-0017 SHIP decision) left off.

---

## Current state

**Branch**: `benchmark/v3.6-ab-20260423-191315`. 11 commits ahead of origin (10 iter commits + 1 HANDOFF rewrite + this iter-0017 commit).

**HEAD (committed)**: iter-0017 ← `775f761` HANDOFF rewrite ← `20f6f07` iter-0014 ← `435680c` iter-0013 ← `47fb504` iter-0012 ← `5c790bc` iter-0011 ← `df623ce` iter-0010 ← `af3a4de` iter-0009 HANDOFF ← `e9233bd` iter-0009. Working tree clean except untracked `.claude/` install dir.

iter-0007 verdict realized. iter-0008 REJECTED. **iter-0009 → iter-0014 + iter-0017 all SHIPPED**. Effective branch state = iter-0017: F1 healthy on 900s budget with full per-phase state observability + archive script path fixed + skill-sync gap auto-healed by `run-suite.sh`. F2/F4/F5/F6/F9 not yet re-verified under iter-0014/0017.

**Next iteration: iter-0016 (full-suite verification under iter-0014/0017). Now safer to run because iter-0017 closed the manual-sync risk. Cost: ~1 hour wall, ~$10-20 spend.**

---

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

1. **Read `autoresearch/HANDOFF.md` first** (this file).
2. `cd /Users/aipalm/Documents/GitHub/devlyn-cli && git status && git log --oneline -8` — confirm branch state matches the HEAD chain above.
3. `diff -rq config/skills/ .claude/skills/ 2>&1 | grep -v "Only in"` — must be silent before any benchmark run.
4. `bash scripts/lint-skills.sh` — must pass all 10 checks before any commit.
5. **All Codex collaboration goes through the local CLI**, never MCP. User direction (memory: `feedback_codex_cross_check.md`). Pattern: `bash config/skills/_shared/codex-monitored.sh -C /Users/aipalm/Documents/GitHub/devlyn-cli -s read-only -c model_reasoning_effort=xhigh "<prompt>"`.
6. Reason independently first; consult Codex with rich evidence; never delegate the decision.

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
