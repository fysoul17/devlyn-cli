# HANDOFF — for the next session

**Read this first** in any new conversation continuing the AutoResearch loop. Smallest set of pointers that lets you pick up where 2026-04-27 (post-iter-0009 SHIP decision) left off.

---

## Current state

**Branch**: `benchmark/v3.6-ab-20260423-191315`. 2 commits ahead of origin (iter-0009 build NOT YET committed — pending commit on this iter's SHIP verdict).

**HEAD (committed)**: `1ff7534` (`Revert "autoresearch(iter-0006): foreground-only codex execution contract"`). **Working tree** carries iter-0009 changes (wrapper + PATH shim + canonical doc edits + harness extension + lint extension); the iter-0009 commit is the next thing to land.

iter-0007 verdict realized. iter-0008 (prompt-level narrow kill-shape contract) ATTEMPTED 2026-04-27 and REJECTED — F6 catastrophic reproduced iter-0006. iter-0009 (executable enforcement: wrapper + PATH shim, NOT hook per codex Round 1) ATTEMPTED 2026-04-27 and **SHIPPED** — F2 BUILD ran 399.9s through wrapper without watchdog kill, F6 collapse +60-point recovery, F1 informationally neutral.

**Reason for revert**: iter-0007 F6 isolation experiment (2 single-fixture runs, 1hr total) established **causality** that iter-0006's contract directly broke F6:

| | Run 1 (iter-0006 HEAD F6 alone) | Run 2 (d895ffa F6 alone) |
|---|---|---|
| variant_score | 35 | 93 |
| diff_bytes | 0 | 5248 |
| files_changed | 0 | 3 |
| transcript bytes | **0 (empty)** | 2213 |
| timed_out / exit | True / 124 (watchdog) | False / 0 (clean) |

Same fixture, same harness, same skill chain, same fixture metadata.timeout — only difference is iter-0006's 19+2 lines of foreground-only contract. **+58 score swing when contract removed.** Not noise — qualitative collapse.

**Mechanism (Codex Round 17)**: foreground codex monopolizes orchestrator for ~10 min Bash dispatch. After it returns, orchestrator does not recover stream control, transcript stays empty, watchdog kills. Universal "foreground-only" rule is too broad.

---

## Decided next step — iter-0010 (production rollout) + commit iter-0009

**iter-0009 SHIPPED 2026-04-27** with full data in `iterations/0009-wrapper-and-hook.md`. Headline metrics:

| Fixture | iter-0008 | iter-0009 | Note |
|---|---|---|---|
| F1 | variant 97/+7/timed_out=true | variant 98/+9/timed_out=true | iter-0009 doesn't fix the F1 separate non-codex starvation; queued as iter-0012 |
| F6 | variant 35/-59/0 files/1500s wall | **variant 95/+5/2 files/290s clean** | catastrophic-collapse FIXED; +60 swing on identical fixture |
| F2 | (not run) | **variant 93/+8/3 files/1126s clean** | wrapper EXERCISED — 399.9s BUILD bash dispatch via `bash codex-monitored.sh ...`; byte-watchdog defeated; full pipeline completed |

**Key empirical finding**: prompt-level instruction is dead (iter-0008), and **a hook is too easy to evade** (Codex Round 1 caught — `bash -lc`, scripts, indirection, plus `--dangerously-skip-permissions` interaction unverified). The right binding is a **PATH shim** that catches every `codex` resolution at the shell layer. The wrapper does the shape enforcement (`< /dev/null` stdin, full stdout streaming, heartbeat-on-stderr every 30s, signal forwarding, exit-code preservation, refusal of piped stdout via `[ -p /dev/stdout ]`).

Codex Round 2 caught the load-bearing wrapper bug: **shim alone doesn't defeat `| tail -200`** because tail still buffers. Wrapper now refuses pipe-stdout with exit 64 + clear message.

**Shipped components (post-Round-1 + Round-2):**

1. `config/skills/_shared/codex-monitored.sh` (NEW). Wrapper. Refuses pipe-stdout, streams full stdout (no `tail -n`), heartbeat sidecar @ 30s on stderr, signal traps forwarding TERM/INT to codex child + sidecar, exact exit-code preservation. ~90 lines.
2. `scripts/codex-shim/codex` (NEW). PATH shim with self-stripping (handles wrapper-of-wrapper chains like Superset's `~/.superset/bin/codex`). ~80 lines.
3. `_shared/codex-config.md` (EDIT). Canonical invocations now `bash .claude/skills/_shared/codex-monitored.sh ...`. Raw `codex exec` documented as forbidden in skill prompts.
4. `engine-routing.md` lines 7 + 74 (EDIT). Wrapper-form Codex call defaults.
5. `auto-resolve/SKILL.md` line 34 (EDIT). Wrapper convention.
6. `benchmark/auto-resolve/scripts/run-fixture.sh` (EDIT, ~30 lines). For variant arm: stage shim PATH in `$WORK_DIR/.devlyn-bin`, write `$WORK_DIR/.claude/settings.json` with `env.PATH` override (since `zsh -c source <snapshot>` overrides parent PATH — discovered mid-build), set `CODEX_REAL_BIN` + `CODEX_MONITORED_PATH`.
7. `scripts/lint-skills.sh` (EDIT). Mirror parity Check 6 extended to include `_shared/codex-config.md`, `_shared/codex-monitored.sh`, `engine-routing.md`. New executable-bit check on the wrapper.

---

## Decided next step — commit + iter-0010

```bash
cd /Users/aipalm/Documents/GitHub/devlyn-cli

# 1. Commit iter-0009 (per autoresearch convention — SHIPPED iters get a commit)
git add config/skills/_shared/codex-monitored.sh \
        scripts/codex-shim/codex \
        config/skills/_shared/codex-config.md \
        config/skills/devlyn:auto-resolve/references/engine-routing.md \
        config/skills/devlyn:auto-resolve/SKILL.md \
        benchmark/auto-resolve/scripts/run-fixture.sh \
        scripts/lint-skills.sh \
        autoresearch/iterations/0008-narrow-kill-shape-contract.md \
        autoresearch/iterations/0009-wrapper-and-hook.md \
        autoresearch/HANDOFF.md
# also stage .claude/skills/* mirror parity if installer didn't run
git commit -m "autoresearch(iter-0009): wrapper + PATH shim — defeat iter-0008 starvation"

# 2. iter-0010 — production rollout (codex Round 2 finding #3 deferred)
#    a. ideate/SKILL.md:245 + :300 — wrapper invocation
#    b. ideate/codex-critic-template.md — wrapper invocation
#    c. preflight/SKILL.md:117 — wrapper invocation
#    d. team-resolve/SKILL.md, team-review/SKILL.md inline sites — wrapper invocation
#    e. package.json files array — ship `scripts/codex-shim/**`
#    f. Document the user-install installer flow that puts shim on PATH globally for /devlyn:* runs
#
# 3. iter-0011 — `timed_out` derivation fix (codex Round 2 finding #2)
#    `result.json` derives timed_out from `elapsed >= timeout` (line 477) instead of
#    the watchdog flag (line 301). At-boundary natural exits misclassified.
#
# 4. iter-0012 — F1 non-codex starvation
#    F1 reproducibly hits 480s cap with empty transcript. Auto-resolve pipeline
#    doesn't naturally exit cleanly after Stop on trivial fixtures. NOT iter-0009's
#    mechanism — separate diagnostic iter needed.
#
# 5. iter-0013 — silent-catch fixture spec
#    F2 spec language doesn't preempt `catch { return fallback }` in BUILD prompts.
#    Both arms produced the pattern. Tighten spec.
```

---

## Critical gotcha — ALWAYS check before any benchmark run

**Skill sync gap.** Variant arm reads from `$REPO_ROOT/.claude/skills/`, but iteration commits land in `config/skills/`. The two trees only sync via `node bin/devlyn.js -y` or surgical `cp`. **Confirmed needed after every git checkout / revert** that touches the iter-0006 contract files.

```bash
diff -rq config/skills/ .claude/skills/ 2>&1 | grep -v "Only in"
```
Expected: silence (UNSHIPPED_SKILL_DIRS legitimately have `Only in config/skills/...` lines per `bin/devlyn.js` exclusion list).

**iter-0010 candidate (queued)**: pre-run rsync mirror at top of `run-suite.sh` for self-healing.

---

## Cross-judge sidecar — iter-0006-full data captured

`benchmark/auto-resolve/results/20260426T034926Z-1ac7594-iter-0006-full/cross-judge-summary.json` has Opus 4.7 dual-judge data over the same sanitized prompts. Pearson(margins)=0.988, winner_agree=6/9, sign_agree=7/9. Mild self-judgment bias signal (~5.6pt — GPT-5.5 inflates variant scores relative to Opus). Permanent dual-judge in `judge.sh` queued post-iter-0008 settle (see `memory/project_dual_judge_2026_04_26.md`).

---

## What is shipped vs queued (post iter-0009 SHIP)

### Shipped on this branch

DECISIONS.md is canonical. iter 0001 (skill scope-first + trivial-fast routing), iter 0002 (F6/F7 spec annotation), iter 0003 (process-group watchdog), iter 0004 (outer claude -p MCP isolation), iter 0005 REVERTED, iter 0006 REVERTED (per iter-0007 verdict), iter 0007 (F6 isolation experiment, conclusive), iter 0008 REJECTED (prompt-level contract empirically dead), **iter-0009 SHIPPED** (wrapper + PATH shim — F2 BUILD ran 399.9s through wrapper without watchdog kill, F6 +60-point recovery from iter-0008 collapse).

Effective branch state = iter-0009. F1 still hits a separate non-codex starvation (iter-0012 candidate); F2 + F6 healthy; F4/F5/F9 status unchanged from baseline (full-suite re-run not yet performed under iter-0009).

### Queued (next hypotheses, ordered, post iter-0009)

1. **iter-0010 — production rollout of wrapper + shim**. Update inline `codex exec` mentions in `ideate/SKILL.md`, `ideate/codex-critic-template.md`, `preflight/SKILL.md`, `team-resolve/SKILL.md`, `team-review/SKILL.md` to use the wrapper. Ship `scripts/codex-shim/codex` to user installs (extend `package.json` `files` array, document the user-installer flow that puts shim on PATH for `/devlyn:*` runs). Codex Round 2 finding #3.
2. **iter-0011 — `timed_out` derivation fix**. `result.json` derives `timed_out` from `elapsed >= timeout` (`run-fixture.sh:477`) instead of the watchdog flag at `:301`. At-boundary natural exits misclassified. Codex Round 2 finding #2.
3. **iter-0012 — F1 non-codex starvation**. F1 reproducibly hits 480s cap with empty transcript even when no codex involvement (variant uses pure Claude tools). Auto-resolve pipeline doesn't naturally exit cleanly after Stop on trivial fixtures. Diagnostic iter needed.
4. **iter-0013 — silent-catch fixture spec**. F2 spec language allows BUILD output with `catch { return fallback }`; both arms produced this pattern, hitting the no-silent-catches disqualifier. Tighten F2 (and similar) spec language to preempt the pattern.
5. **iter-0014 — F9 wall-time regression** (was iter-0009 in old queue). Both iter-0006 single-fixture F9 attempts took >30 min. Diagnostic: bump F9 metadata.timeout to 5400s.
6. **iter-0015 — sync-gap auto-mirror fix** (codex round 7 Option A). Pre-run rsync mirror at top of `run-suite.sh` for self-healing of `config/skills/` ← `.claude/skills/` drift.
7. **iter-0016 — single-fixture ship-gate hard-floor bug**. Ship-gate currently passes catastrophic regression on N=1 because 7/9 floor not applied at N=1.
8. **iter-0017 — permanent dual-judge in judge.sh** (`memory/project_dual_judge_2026_04_26.md`). Spec ready: arbitration rule, no third-tiebreaker.
9. **iter-0018 — F6 chronic slowness investigation**. F6 variant has been 5–30× slower than bare across all iters. Latent harness-quality issue.
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
11. **Read your own data carefully.** Codex Round 16 caught me misreading my own CSV column order. Double-check before drawing conclusions.
12. **User directions ≠ debate prompts.** When user says "we're going X direction," ask codex for best practice + improvements, NOT "should we?". Surface codex pushback to user transparently. (`feedback_user_directions_vs_debate.md`)
13. **`zsh -c source <snapshot>` overrides parent PATH.** Project-scope `$WORK_DIR/.claude/settings.json` env override is the only reliable way to inject PATH into Bash dispatches inside `claude -p`. Discovered during iter-0009 build. Document for any future PATH-dependent harness work.
14. **`[ -p /dev/stdout ]` is the portable POSIX test for "stdout is a pipe."** macOS `stat -f "%HT" /dev/fd/1` returned spurious "Fifo File" for redirected files inside bash scripts; `[ -p ... ]` is correct. Used in iter-0009 wrapper to refuse pipe-stdout invocations.
15. **Cross-model GAN earned its keep at iter-0009.** Round 1 caught hook fragility (swap to PATH shim). Round 2 caught wrapper pipe-stdout starvation BEFORE benchmark (would have produced false PASS on negative canary). Continue dual-model practice.

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
- **iter-0009 R1**: hook → PATH shim swap (hook bypasses: `bash -lc`, scripts, indirection, `--dangerously-skip-permissions` interaction unverified). Wrapper streams full stdout (no `tail -200`). Cut team-* / ideate / preflight inline rewrites.
- **iter-0009 R2**: `| tail -200` defeats wrapper streaming → wrapper must refuse pipe-stdout via `[ -p /dev/stdout ]`. Heartbeat/metadata to stderr (cleaner stdout = codex output). Mirror parity for `engine-routing.md`. F2 expectation: regression check, not direct wrapper proof — caveat applied.

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
- `project_dual_judge_2026_04_26.md` — DECIDED, A sidecar shipped, B queued as iter-0012.
- `project_skill_guardrails_2026_04_26.md` — **NEW** — G1-G5 design constraints from iter-0006/0007.
