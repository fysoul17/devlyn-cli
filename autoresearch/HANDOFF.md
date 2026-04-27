# HANDOFF — for the next session

**Read this first** in any new conversation continuing the AutoResearch loop. Smallest set of pointers that lets you pick up where 2026-04-27 (post-iter-0014 SHIP decision) left off.

---

## Current state

**Branch**: `benchmark/v3.6-ab-20260423-191315`. 9 commits ahead of origin once iter-0014 is committed.

**HEAD (committed)**: `e9233bd` iter-0009 → `af3a4de` iter-0009 HANDOFF → `df623ce` iter-0010 → `5c790bc` iter-0011 → `47fb504` iter-0012 → `435680c` iter-0013 → **`<iter-0014 commit pending>`**. Working tree clean except untracked `.claude/` install dir.

iter-0007 verdict realized. iter-0008 REJECTED. iter-0009 through iter-0013 SHIPPED. **iter-0014 SHIPPED 2026-04-27** — state-writes-per-phase observability + archive script path fix. Codex iter-0014 R0 caught two things: D4-lite design (universal block + per-phase reminders + targeted prompt-body fixes — defense in depth) and a separate archive script path bug (`python3 scripts/archive_run.py` fails from work_dir; lives at `.claude/skills/devlyn:auto-resolve/scripts/archive_run.py`). Empirical F1 verification: state.phases populated for `build, build_gate, evaluate, final_report` with started_at/completed_at/duration_ms; archive moved artifacts to `.devlyn/runs/ar-...`. Same `verify_score=0.8`, elapsed=610s under 900s budget.

**Next iteration: iter-0015 candidate — shim distribution (still deferred per Karpathy #2 unless production regression observed), or queue items below. Pick by current pain.**

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

### Option A: iter-0015 — shim distribution to user installs (deferred)

Still deferred per Karpathy #2 (Simplicity First — speculative defense for unobserved-in-prod regression). iter-0011 closed the most likely leak vector (Check 10 evasion-shape gap) at far lower cost. Revisit when production regression observed OR a stronger leak signal arrives.

If revived: design constraints (from iter-0010 R1 + iter-0011 R0 with Codex):
- Shim must be **fail-open** when env vars unset (do not retain `exit 127`; pass through to real codex).
- Activation via `bin/devlyn.js doctor activate` (or `devlyn init`), **NOT npm post-install** (avoids `--ignore-scripts` brittleness).
- Idempotent merge into project `.claude/settings.json env` (prepend PATH only if missing; never clobber existing env).

### Recommendation

No urgent pain remains. **Option A** stays deferred. Likely next move: full-suite re-run under iter-0014 to confirm F2/F4/F6/F9 all benefit from the new state-write protocol + archive fix; then revisit queue.

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

DECISIONS.md is canonical. iter 0001 (skill scope-first + trivial-fast routing), iter 0002 (F6/F7 spec annotation), iter 0003 (process-group watchdog), iter 0004 (outer claude -p MCP isolation), iter 0005 REVERTED, iter 0006 REVERTED (per iter-0007 verdict), iter 0007 (F6 isolation experiment, conclusive), iter 0008 REJECTED (prompt-level contract empirically dead), iter-0009 SHIPPED (wrapper + PATH shim — F2 BUILD ran 399.9s through wrapper without watchdog kill, F6 +60-point recovery from iter-0008 collapse), iter-0010 SHIPPED (production rollout of wrapper-form to ideate / preflight / team-resolve / team-review; lint Check 10 added as static gate; shim shipping deferred per Codex Round 1 ship-blocker), iter-0011 SHIPPED (Codex-collaborated Option D: Check 10 evasion-shape close — pattern broadened to invocation-class — plus priming-token scrub in shared docs; falsification canary 6/6), iter-0012 SHIPPED (`run-fixture.sh` `timed_out` derivation now sources WATCHDOG_FIRED Bash sentinel instead of `elapsed >= timeout`; clean signal for natural exits at-or-past budget; Codex pre-edit R0 caught `set -u` init order + invariant misstatement), iter-0013 SHIPPED (F1 timeout discriminator: 480→900s metadata bump confirmed by single 465s-clean run; HANDOFF's "doesn't exit cleanly" framing was empirically wrong; pipeline overhead + Codex BUILD variance explain the 10x bare/variant gap; state-writes-per-phase observability drift filed), **iter-0014 SHIPPED** (state-writes-per-phase observability + archive script path. Codex iter-0014 R0: D4-lite design (universal block + per-phase reminders + targeted prompt-body fixes) + caught separate archive script path bug (`scripts/archive_run.py` fails from work_dir; lives at `.claude/skills/devlyn:auto-resolve/scripts/`). Empirical F1 verification: phases.{build, build_gate, evaluate, final_report} all populated with started_at/completed_at/duration_ms; archive ran).

Effective branch state = iter-0014. F1 healthy on 900s budget with full state observability + archive; F2/F4/F6/F9 not yet re-verified under iter-0014.

### Queued (next hypotheses, ordered, post iter-0014)

1. **iter-0015 — shim distribution to user installs** (deferred from iter-0010 per Codex R1 ship-blocker; remained deferred at iter-0011/0012/0013/0014 per Karpathy #2). Design fail-open shim + `devlyn doctor activate` (NOT npm post-install) + idempotent settings.json merge. Revisit when production regression observed.
2. **iter-NEXT — full-suite verification under iter-0014**. Run F2/F4/F6/F9 to confirm state-write protocol + archive fix carry over. May surface follow-up observability gaps for non-fast routes (CRITIC, DOCS phases).
3. **iter-NEXT+1 — `claude -p --output-format stream-json`** for variant arm. Would make transcript flush incrementally and survive SIGTERM partial output. Optional; not pressing once F1 budget is right.
4. **iter-0015 — silent-catch fixture spec**. F2 spec language allows BUILD output with `catch { return fallback }`; tighten F2 (and similar) spec language.
5. **iter-0016 — F9 wall-time regression**. Both iter-0006 single-fixture F9 attempts took >30 min. Bump F9 metadata.timeout to 5400s.
6. **iter-0017 — sync-gap auto-mirror fix** (codex round 7 Option A). Pre-run rsync mirror at top of `run-suite.sh`.
7. **iter-0018 — single-fixture ship-gate hard-floor bug**. Ship-gate currently passes catastrophic regression on N=1 because 7/9 floor not applied at N=1.
8. **iter-0019 — permanent dual-judge in judge.sh** (`memory/project_dual_judge_2026_04_26.md`).
9. **iter-0020 — F6 chronic slowness investigation**.
10. **iter-0021 — auto-resolve stuck-execution abort criteria** (skill guardrail G5).
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
- **iter-0011 R0**: I proposed B → C → defer A (Karpathy #2 — A is speculative defense). Codex concurred but flagged a real risk class — runtime emission drift (`codex exec "<prompt>"` quoted-prompt evasion shape that current Check 10 misses). Proposed Option D = cheap hardening (broaden Check 10 + scrub residual priming tokens). Confirmed B and C are independent (F1 timeout is real, not misclassification). Adopted D as iter-0011; B = iter-0012, C = iter-0013, A = iter-0014 still deferred.
- **iter-0012 R0**: pre-edit read-only review of 5-line `timed_out` derivation fix. Codex verdict: surgical change is right. Five precise corrections/cautions: (1) invariant (ii) misstatement — `elapsed=TIMEOUT-1` was already correct under `>=`; the genuine mislabels are `elapsed == TIMEOUT` exactly + clean exits >TIMEOUT where watchdog didn't fire. (2) **`set -u` caution** — initialize `WATCHDOG_FIRED=0` BEFORE `if DRY_RUN` branch or `export INVOKE_EXIT WATCHDOG_FIRED` tears down dry-run paths. (3) Don't derive timeout from `INVOKE_EXIT==124` (124 is a legal natural exit code). (4) Don't add `watchdog_killed` schema field (duplicates corrected `timed_out`). (5) Don't touch SIGTERM grace (existing behavior; no longer leaks into `timed_out` after fix). (6) Race on `kill -0` is real but narrow — defer to a future Python timeout wrapper.
- **iter-0013 R0**: pre-discriminator design review. I proposed a reframe of HANDOFF's "doesn't exit cleanly after Stop" framing based on debug-log evidence. Codex pushed back on three things: (1) my "0.6s away from natural exit" claim was over-asserted — SessionEnd hooks completing at status 0 can be SIGTERM cleanup, not natural completion. (2) F1 didn't actually complete the fast route — `evaluate.*` artifacts missing, ran cut off mid-EVAL. (3) The 268.5s Bash dispatch (Codex's own grep of debug log) is the dominant time sink — not a uniform PARSE+BUILD+BUILD-GATE distribution. Codex recommendation: skip pure "close as benchmark config" and run the 900s discriminator first. Outcome A (clean PASS, elapsed=465, transcript=2304 bytes, evaluate.* present, verdict=PASS_WITH_ISSUES) confirmed the reframe but with Codex's corrections folded in.
- **iter-0014 R0**: pre-edit design review of state-writes-per-phase fix. I presented 4 options (D1=universal block alone, D2=per-prompt edits alone, D3=both, D4=per-phase SKILL.md additions). Codex verdict: (1) D1 alone insufficient (top-level guidance gets glossed over at action sites). (2) D2 alone also insufficient (`build-gate.md` already had explicit prompt-body output contract and orchestrator still skipped the write empirically). (3) Use **D4-lite**: universal block + per-phase salience reminders + targeted prompt-body fixes. (4) **Pushback on knock-on bug claim**: I'd connected missing-archive symptom to missing-final_report.verdict; Codex read `archive_run.py` and refuted — the script moves artifacts unconditionally; verdict only gates pruning. Real cause was simpler: SKILL.md's `python3 scripts/archive_run.py` path doesn't resolve in work_dir. (5) True dry-run not available (orchestrator is prompt-driven); single canary run on F1 with assertions on phase-keys + archive directory. Outcome verified all 4 phases populated + archive ran.

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
- `project_iter0010_shipped_2026_04_27.md` — production rollout + shim shipping deferred.
- `project_iter0011_shipped_2026_04_27.md` — Codex Option D: Check 10 evasion-shape close + priming-scrub.
- `project_iter0012_shipped_2026_04_27.md` — `timed_out` derivation switched to WATCHDOG_FIRED sentinel.
- `project_iter0013_shipped_2026_04_27.md` — F1 timeout discriminator: 480→900s; HANDOFF reframe corrected; state-write drift filed.
- `project_iter0014_shipped_2026_04_27.md` — **NEW** — state-writes-per-phase + archive script path. D4-lite via Codex R0; empirical F1 verification.
