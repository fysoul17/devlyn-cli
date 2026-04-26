# HANDOFF — for the next session

**Read this first** in any new conversation continuing the AutoResearch loop. Smallest set of pointers that lets you pick up where 2026-04-26 (post-iter-0007 REVERT decision) left off.

---

## Current state

**Branch**: `benchmark/v3.6-ab-20260423-191315`.

**HEAD**: `1ac7594` (iter-0006 foreground-only contract). **Status: REVERT pending user authorization.** When user approves, run `git revert 1ac7594 --no-edit` and sync `.claude/skills/` to match the reverted `config/skills/`.

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

## Decided next step — iter-0008: narrow kill-shape contract

After REVERT, design a narrower contract that targets the EXACT failure class from iter-0005 F2 collapse — not all backgrounding.

- ✗ "All `codex exec` must be foreground" (iter-0006 — too broad, broke F6).
- ✓ **iter-0008 hypothesis**: ban only orphaned/unmonitored background codex. Allow background codex paired with active observation (tail -f / poll process / progress emission to keep orchestrator stream alive).

Falsification gate before any full suite:
1. F2 alone (was the original failure shape iter-0006 fixed) — must show recovery (margin ≥ +5).
2. F6 alone (was the regression iter-0006 caused) — must NOT collapse (variant_score ≥ 85, files ≥ 1, verify ≥ 0.66, transcript > 0 bytes).

Only run full-suite if both pass. The two-fixture gate replaces iter-0006's four-fixture gate per Karpathy #2 (less is more — load-bearing fixtures only).

---

## How to start the next session (iter-0008)

```bash
cd /Users/aipalm/Documents/GitHub/devlyn-cli
git status                              # confirm branch
git log --oneline -3                    # confirm HEAD

# 1. If iter-0006 not yet reverted (ASK USER first)
git revert 1ac7594 --no-edit
# After revert, sync .claude/skills/ to match config/skills/
cp config/skills/_shared/codex-config.md .claude/skills/_shared/codex-config.md
cp config/skills/devlyn:auto-resolve/references/engine-routing.md \
   .claude/skills/devlyn:auto-resolve/references/engine-routing.md
diff -rq config/skills/ .claude/skills/ 2>&1 | grep -v "Only in"  # verify clean

# 2. Read iter-0007 + iter-0008 candidate
cat autoresearch/iterations/0007-f6-isolation.md
cat autoresearch/walltime-history.md      # context
cat memory/project_skill_guardrails_2026_04_26.md  # design constraints

# 3. Design iter-0008 contract (apply skill guardrails G1-G5)
# 4. Two-fixture falsification gate: F2 + F6 single-fixture before any suite
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

## What is shipped vs queued (post iter-0007 REVERT)

### Shipped on this branch (effective post-REVERT)

DECISIONS.md is canonical. iter 0001 (skill scope-first + trivial-fast routing), iter 0002 (F6/F7 spec annotation), iter 0003 (process-group watchdog), iter 0004 (outer claude -p MCP isolation), iter 0005 REVERTED, iter 0006 REVERTED (per iter-0007 verdict).

Effective branch state ≈ iter-0004 effective. Post-revert, F2's iter-0005-class collapse mechanism is back on the table; iter-0008 will surgically address it without breaking F6.

### Queued (next hypotheses, ordered)

1. **Iter 0008 — narrow kill-shape contract** (next session, see above). Two-fixture gate (F2 + F6) before any full suite.
2. **Iter 0009 — F9 wall-time regression** (was queued earlier, still relevant). Both iter-0006 single-fixture F9 attempts took >30 min variant. Diagnostic: bump metadata.timeout for F9 to 5400s.
3. **Iter 0010 — sync-gap auto-mirror fix** (codex round 7 Option A). Pre-run rsync mirror at top of `run-suite.sh`.
4. **Iter 0011 — watchdog classification bug** (codex round 6 deferral). Misclassification of `timed_out` field when watchdog fires near metadata.timeout.
5. **Iter 0012 — permanent dual-judge in judge.sh** (this session decision, see `memory/project_dual_judge_2026_04_26.md`). Spec ready: arbitration rule, no third-tiebreaker.
6. **Iter 0013 — F6 chronic slowness investigation** (separate from contract). F6 variant has been 5-30× slower than bare across all iters. Latent harness-quality issue.
7. **Iter 0014 — auto-resolve stuck-execution abort criteria** (skill guardrail G5).
8. **5-Why operationalization in CLAUDE.md** (codex round 2 Karpathy #1 expansion).
9. **DOCS Job 2 wider verification** (long-queued).
10. **Held-out fixture set** (don't build until 3+ fixtures improve with no intuitive mechanism).
11. **Adversarial-ask layer** (long-term).

### Deferred (user-direction, awaiting explicit user call)

12. Multi-LLM orchestration modes (3 modes + extensibility) — `memory/project_orchestration_modes_2026_04_26.md`.
13. Benchmark cross-mix arms — `memory/project_benchmark_cross_mix_2026_04_26.md`.

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
