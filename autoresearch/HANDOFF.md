# HANDOFF — for the next session

**Read this first** in any new conversation continuing the AutoResearch loop. Smallest set of pointers that lets you pick up where 2026-04-27 (post-iter-0010 SHIP decision) left off.

---

## Current state

**Branch**: `benchmark/v3.6-ab-20260423-191315`. 4 commits ahead of origin (will be 5 once iter-0010 is committed).

**HEAD (committed)**: `e9233bd` iter-0009 → `af3a4de` iter-0009 HANDOFF → **`<iter-0010 commit pending>`**. Working tree clean except untracked `.claude/` install dir (and the iter-0010 commit-ready edits, see "What was just shipped" below).

iter-0007 verdict realized. iter-0008 REJECTED 2026-04-27. iter-0009 SHIPPED 2026-04-27. **iter-0010 SHIPPED 2026-04-27** — production rollout of wrapper-form to ideate / preflight / team-resolve / team-review. Lint Check 10 (no raw `codex exec` invocation in skill prompts) added as static gate.

**Next iteration: open. Top of queue is shim distribution to user installs (deferred from iter-0010 — Codex Round 1 caught the ship-blocker), or iter-0011 `timed_out` derivation fix, or iter-0012 F1 non-codex starvation diagnostic. Pick by current pain.**

---

## What was just shipped (iter-0010)

Full data in `iterations/0010-production-rollout.md`.

7-file diff, +46/-13 lines, no new files, no new abstractions:

1. `config/skills/devlyn:ideate/SKILL.md` — 2 sites (CHALLENGE critic + `--engine codex` full pipeline incl. `resume --last`).
2. `config/skills/devlyn:ideate/references/codex-critic-template.md` — 1 site (template description).
3. `config/skills/devlyn:preflight/SKILL.md` — 1 site (CODE AUDIT auditor).
4. `config/skills/devlyn:team-resolve/SKILL.md` — 4 sites (code block + 3 phrase-priming).
5. `config/skills/devlyn:team-review/SKILL.md` — 4 sites (code block + 3 phrase-priming).
6. `config/skills/_shared/codex-config.md` — 1 site (heartbeat doc bug fix: stdout → stderr).
7. `scripts/lint-skills.sh` — Check 6 mirror parity extended to 3 new files; new Check 10 forbids raw `codex exec` invocation pattern.

Falsification gate: lint clean (all 10 checks ✓), wrapper canary clean (pipe-stdout → exit 64 with iter-0009 R2 message; file-stdout → exit 0 with `[codex-monitored] start` on stderr), pattern-coverage test verified Check 10 catches single-line, resume, and multi-line `\` shapes.

**DROPPED from iter-0010 scope (Codex Round 1 ship-blocker)**:

- Shipping `scripts/codex-shim/codex` to user installs. Shim hard-fails exit 127 without `CODEX_REAL_BIN` + `CODEX_MONITORED_PATH` envs (shim:59–63, :68–72). Benchmark wires those via `run-fixture.sh:90–118` using a project-scoped `.claude/settings.json env.PATH` override (zsh shell-snapshot resets parent PATH inside Bash dispatches). Production user installs have none of that scaffolding; shipping the shim without it would brick `codex` invocations entirely. Defer to a future iteration that designs installer-managed activation.

---

## Decided next step — pick one of:

### Option A: iter-NEXT — shim distribution to user installs (designed)

Goal: make the shim available in production user installs without bricking them.

Design constraints (from iter-0010 R1):

- Must NOT hard-fail when env vars unset (current behavior is `exit 127`). Either set sensible defaults or fall through to the real codex.
- PATH wiring must survive zsh shell-snapshot (parent PATH gets reset inside Bash dispatches inside `claude -p`). Project-scoped `.claude/settings.json env.PATH` is the proven mechanism (`run-fixture.sh:117–`).
- Should not require user manual setup (option A in original HANDOFF) because skipped setup = silently no safety net = same as not shipping.

Likely shape: `bin/devlyn.js` post-install step (a) detects `CODEX_REAL_BIN = $(command -v codex)`, (b) writes shim into `<install-dir>/.devlyn-bin/codex`, (c) updates project-scoped `.claude/settings.json` with `env.PATH = "$INSTALL_DIR/.devlyn-bin:$PARENT_PATH"`, `env.CODEX_REAL_BIN`, `env.CODEX_MONITORED_PATH`. Optional: `bin/devlyn.js doctor` subcommand to verify activation.

Cross-check with Codex before any code change. The activation path is the load-bearing question.

### Option B: iter-0011 — `timed_out` derivation fix (smaller, surgical)

`result.json` derives `timed_out` from `elapsed >= timeout` (`run-fixture.sh:477`) instead of the watchdog flag at `:301`. At-boundary natural exits get misclassified. Codex Round 2 (iter-0008) finding #2.

### Option C: iter-0012 — F1 non-codex starvation diagnostic

F1 reproducibly hits 480s cap with empty transcript even when no codex involvement (variant uses pure Claude tools). Auto-resolve pipeline doesn't naturally exit cleanly after Stop on trivial fixtures. Diagnostic iter — instrument and observe rather than fix.

### Recommendation

**Option A first** — it closes the production gap iter-0010 left open (shim safety net for users). iter-0011/iter-0012 are smaller and don't block user-facing chain quality. But A requires a designed approach and Codex cross-check before code change.

---

## Critical gotcha — ALWAYS check before any benchmark run

**Skill sync gap.** Variant arm reads from `$REPO_ROOT/.claude/skills/`, but iteration commits land in `config/skills/`. The two trees only sync via `node bin/devlyn.js -y` or surgical `cp`. **Confirmed needed after every git checkout / revert** that touches the iter-0006 contract files OR any of the iter-0010-rewritten files.

```bash
diff -rq config/skills/ .claude/skills/ 2>&1 | grep -v "Only in"
```
Expected: silence (UNSHIPPED_SKILL_DIRS legitimately have `Only in config/skills/...` lines per `bin/devlyn.js` exclusion list).

**iter-0015 candidate (queued)**: pre-run rsync mirror at top of `run-suite.sh` for self-healing.

---

## Cross-judge sidecar — iter-0006-full data still relevant

`benchmark/auto-resolve/results/20260426T034926Z-1ac7594-iter-0006-full/cross-judge-summary.json` has Opus 4.7 dual-judge data over the same sanitized prompts. Pearson(margins)=0.988, winner_agree=6/9, sign_agree=7/9. Mild self-judgment bias signal (~5.6pt — GPT-5.5 inflates variant scores relative to Opus). Permanent dual-judge in `judge.sh` queued (see `memory/project_dual_judge_2026_04_26.md`).

---

## What is shipped vs queued (post iter-0010 SHIP)

### Shipped on this branch

DECISIONS.md is canonical. iter 0001 (skill scope-first + trivial-fast routing), iter 0002 (F6/F7 spec annotation), iter 0003 (process-group watchdog), iter 0004 (outer claude -p MCP isolation), iter 0005 REVERTED, iter 0006 REVERTED (per iter-0007 verdict), iter 0007 (F6 isolation experiment, conclusive), iter 0008 REJECTED (prompt-level contract empirically dead), iter-0009 SHIPPED (wrapper + PATH shim — F2 BUILD ran 399.9s through wrapper without watchdog kill, F6 +60-point recovery from iter-0008 collapse), **iter-0010 SHIPPED** (production rollout of wrapper-form to ideate / preflight / team-resolve / team-review; lint Check 10 added as static gate; shim shipping deferred per Codex Round 1 ship-blocker).

Effective branch state = iter-0010. F1 still hits a separate non-codex starvation (iter-0012 candidate); F2 + F6 healthy; F4/F5/F9 status unchanged from baseline (full-suite re-run not yet performed under iter-0009 or iter-0010).

### Queued (next hypotheses, ordered, post iter-0010)

1. **iter-NEXT — shim distribution to user installs** (deferred from iter-0010 per Codex Round 1 ship-blocker). Design installer-managed activation: bin/devlyn.js post-install detects `CODEX_REAL_BIN`, stages shim, writes project-scoped `.claude/settings.json env.PATH/CODEX_REAL_BIN/CODEX_MONITORED_PATH`. Cross-check with Codex before code change.
2. **iter-0011 — `timed_out` derivation fix**. `result.json` derives `timed_out` from `elapsed >= timeout` (`run-fixture.sh:477`) instead of the watchdog flag at `:301`. At-boundary natural exits misclassified.
3. **iter-0012 — F1 non-codex starvation**. F1 reproducibly hits 480s cap with empty transcript even when no codex involvement.
4. **iter-0013 — silent-catch fixture spec**. F2 spec language allows BUILD output with `catch { return fallback }`; tighten F2 (and similar) spec language.
5. **iter-0014 — F9 wall-time regression**. Both iter-0006 single-fixture F9 attempts took >30 min. Bump F9 metadata.timeout to 5400s.
6. **iter-0015 — sync-gap auto-mirror fix** (codex round 7 Option A). Pre-run rsync mirror at top of `run-suite.sh`.
7. **iter-0016 — single-fixture ship-gate hard-floor bug**. Ship-gate currently passes catastrophic regression on N=1 because 7/9 floor not applied at N=1.
8. **iter-0017 — permanent dual-judge in judge.sh** (`memory/project_dual_judge_2026_04_26.md`).
9. **iter-0018 — F6 chronic slowness investigation**.
10. **iter-0019 — auto-resolve stuck-execution abort criteria** (skill guardrail G5).
11. **5-Why operationalization in CLAUDE.md** (codex round 2 Karpathy #1 expansion).
12. **DOCS Job 2 wider verification** (long-queued).
13. **Held-out fixture set** (don't build until 3+ fixtures improve with no intuitive mechanism).
14. **Adversarial-ask layer** (long-term).

### Deferred (user-direction, awaiting explicit user call)

- Multi-LLM orchestration modes (3 modes + extensibility) — `memory/project_orchestration_modes_2026_04_26.md`.
- Benchmark cross-mix arms — `memory/project_benchmark_cross_mix_2026_04_26.md`.

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
9. **Self-judgment bias** is real (~5.6pt). Permanent dual-judge queued.
10. **Universal contract rules over-fit single failure modes.** iter-0006 banned a category to prevent a specific shape; the category is broader than the shape. Apply skill guardrails G1-G5 (`memory/project_skill_guardrails_2026_04_26.md`) before merging any contract change.
11. **Read your own data carefully.** Codex Round 16 caught me misreading my own CSV column order.
12. **User directions ≠ debate prompts.** When user says "we're going X direction," ask codex for best practice + improvements, NOT "should we?". Surface codex pushback to user transparently. (`feedback_user_directions_vs_debate.md`)
13. **`zsh -c source <snapshot>` overrides parent PATH.** Project-scope `$WORK_DIR/.claude/settings.json` env override is the only reliable way to inject PATH into Bash dispatches inside `claude -p`. Discovered during iter-0009 build.
14. **`[ -p /dev/stdout ]` is the portable POSIX test for "stdout is a pipe."** Used in iter-0009 wrapper to refuse pipe-stdout invocations.
15. **Cross-model GAN earned its keep at iter-0009 AND iter-0010.** iter-0010 R1 caught shim-shipping ship-blocker (hard-fails 127 without env wiring); R2 caught lint Check 10 multiline blind spot before commit. Continue dual-model practice.
16. **Static gate suffices when mechanism is unchanged** (iter-0010 lesson). Text-only changes that ride on an iter-0009-proven mechanism don't need a benchmark gate; lint check + canary is the right scope.
17. **Pattern-priming applies even to descriptive text** (iter-0010 lesson). Phrases like "passes args through to `codex exec` verbatim" leak `codex exec` into the orchestrator's prior even though they're not invocations. Rephrase to drop the token in prompt-facing files.
18. **Lint patterns must cover all syntactic shapes the orchestrator can emit** (iter-0010 R2 lesson). Multi-line `codex exec \` had to be added; single-line-only patterns leave a regression surface.

---

## Codex collaboration log (running)

- R1–R5 (iter 0005): inner-codex flag bundle work.
- R6: expand falsification gate F2→F5→F4→F9→full
- R7: sync-gap fix = Option A
- R8: routing-telemetry observability (later moot)
- R9: F4 score-94 borderline pass
- R10: F9 #1 environmental, RERUN
- R11: F9 #2 strict-fail by criteria
- R12: harness-truth halt — RETRACTED in R13
- R13: confirm retraction, run full-suite
- R14: post-results — DEFER not REVERT, F6 isolation as iter-0007
- R15: strategic check — fold iter-0008 wall-time into iter-0007, cut iter-0012 for now
- R16: caught data-misread (F6 prior 0-files claim wrong; F4/F5 noise → "shared runtime/API failure")
- R17: post-isolation — REVERT confirmed; iter-0008 = narrow kill-shape ban
- iter-0009 R1: hook → PATH shim swap. Wrapper streams full stdout (no `tail -200`).
- iter-0009 R2: `| tail -200` defeats wrapper streaming → wrapper must refuse pipe-stdout via `[ -p /dev/stdout ]`. Heartbeat to stderr (cleaner stdout = codex output). Mirror parity for `engine-routing.md`.
- **iter-0010 R1**: shim-shipping ship-blocker (hard-fails 127 without env wiring). 2 phrase-priming sites missed (team-resolve:147, team-review:88). Heartbeat doc bug at canonical:54 (said stdout, wrapper writes stderr). Verdict drove scope cut: drop shim shipping from iter-0010, defer.
- **iter-0010 R2**: lint Check 10 multi-line blind spot caught before commit (pattern missed `codex exec \` continuation). 3 residual descriptive `codex exec` mentions in prompt bodies should be rephrased to remove priming token. Wrapper `resume --last` shape verified correct (line 114 produces valid `codex exec resume --last`).

---

## Memory entries that matter (cumulative)

(stored in `~/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/memory/`)

- `feedback_codex_cross_check.md` — dual-model GAN pattern.
- `feedback_auto_resolve_autonomy.md` — hands-free contract.
- `feedback_user_directions_vs_debate.md` — user directions are decisions, surface codex pushback.
- `project_v3_*.md` — historical harness redesign series.
- `project_autoresearch_framework_2026_04_25.md` — framework genesis.
- `project_skill_sync_gap_2026_04_26.md` — sync-gap gotcha.
- `project_orchestration_modes_2026_04_26.md` — DEFERRED, user-direction.
- `project_benchmark_cross_mix_2026_04_26.md` — DEFERRED, user-direction.
- `project_dual_judge_2026_04_26.md` — DECIDED, A sidecar shipped, B queued as iter-0017.
- `project_skill_guardrails_2026_04_26.md` — G1-G5 design constraints from iter-0006/0007.
- `project_iter0009_shipped_2026_04_27.md` — wrapper + PATH shim ship details.
- `project_iter0010_shipped_2026_04_27.md` — **NEW** — production rollout + shim shipping deferred.
