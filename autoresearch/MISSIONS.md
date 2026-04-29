# MISSIONS — sequenced focus for devlyn-cli

This file is the **mission roadmap** for devlyn-cli. Only the current mission's gates bind day-to-day work. Future missions are visible here so the loop never forgets where we are going, but they do **not** bind iter-by-iter decisions until their predecessor is unblocked.

The contract is hard:

> **Do not start the next mission until the current one is unblocked. One mission, one focus.**

The user's standing directive (HANDOFF "STANDING USER DIRECTIVE" block) is the source of truth above this file. If a mission gate conflicts with the standing directive, the directive wins.

---

## 🎯 MISSION 1 (active, 2026-04-29 →) — Single-task skill excellence on `main`

**Frame**: one user, one task, one working tree on `main`. No parallel runs. No worktree per task. The skill (`/devlyn:auto-resolve`, optionally chained with `/devlyn:ideate` + `/devlyn:preflight`) must be **extremely** more accurate, more effective, and reasonably faster than a bare end-user prompting Claude or Codex directly on the same task.

**Why this is mission 1, not mission 2 or 3**: parallel-fleet readiness, multi-agent organisation, run-isolation infrastructure are all *amplifiers* — they multiply whatever single-task value the skill already delivers. If single-task value is marginal, multiplying it gives marginal × N = still marginal. iter-0020's L2 architecture failed exactly this test: pair-mode lost on accuracy at the single-task level. There is no point shipping parallel infra over a single-task surface that isn't yet world-class.

**Mission gates (release blockers — every gate must hold before Mission 2 starts)**:

1. **L1 vs L0 (single-task quality)** — single-engine harness (`--engine claude` OR `--engine codex`) beats the same engine bare on the 4-axis judge rubric (Spec / Constraint / Scope / Quality), per NORTH-STAR.md operational test #1: suite-avg margin ≥ +8 (preferred) or ≥ +5 (floor) across ≥ 7 of 9 fixtures. **Currently FAILING**: iter-0020 9-fixture data showed L1-L0 = +4.4, below the +5 floor.

2. **L1 vs L0 (single-task efficiency)** — per NORTH-STAR.md ops test #2: L1 must beat `bare-best-of-N` where N is the wall-time ratio. No fixture where L1 ties or loses on quality with wall ratio ≥ 1.0.

3. **L2 vs L1 (single-task pair value)** — if a pair-mode L2 ships, it must materially lift quality on pair-eligible fixtures (NORTH-STAR ops test #6) without regressing any fixture (#5). **Currently DISABLED**: iter-0020 closed L2 (Codex BUILD + Claude review) as failed-experiment 2026-04-29; iter-0021 inverted-pair (Claude BUILD + Codex CRITIC) is the open research path.

4. **No hard floors broken** — zero variant-arm CRITICAL findings, zero variant-arm HIGH `design.*` / `security.*` findings, zero variant watchdog timeouts (NORTH-STAR ops test #3).

5. **Real-project trial passes** — NORTH-STAR ops test #14: one fresh real-project task (not fixture) ships under `/devlyn:auto-resolve` end-to-end without prompt-engineering rescue.

**Categorical reliability (Codex GPT-5.5 verdict 2026-04-29, ultimate-goal consult)** — per Q2 of that consult, "overwhelmingly better" is *not* an average margin number; it is **expected utility under categorical reliability**. The harness must systematically *not* fail the task classes bare prompting systematically *does* fail (spec-compliance, multi-file scope, build-gate-detected runtime errors, security CRITICAL findings, silent-catch / hardcoded-value / `any` / `@ts-ignore` violations, scope leaks). Mission 1 ships only when this asymmetry is empirically clear, not when an average lift hits a number.

**Open iter (Mission 1 work-in-progress)**:
- iter-0021 — Claude BUILD + Codex CRITIC inverted-pair research smoke on F2 / F3 / F8 (the three fixtures with strongest L1 underperformance signal). **Research candidate only** (Codex 2026-04-29 verdict): a 3-fixture PASS does NOT make L2 a product surface — it only earns L2 a candidate slot pending full 9-fixture L1/L2 release-readiness data. NORTH-STAR.md #4 still requires L1 to pass its own gates before L2 ships.
- L1 real-project diagnostic — one fresh `--engine claude` end-to-end run on a real (non-fixture) task; documents whether L1 produces genuinely better output than the same engine bare. This is single-task, single-worktree work — does *not* depend on parallel infra.

**Hard NO list during Mission 1**:
- ❌ No worktree-per-task substrate work. Stays single-worktree on `main`.
- ❌ No parallel-fleet smoke (N≥2 simultaneous runs). Single task only.
- ❌ No resource-lease helper / SQLite leases / port pool. Defaults stay (single dev server on 5173 is fine for one user).
- ❌ No run-scoped state migration (`.devlyn/pipeline.state.json` stays at worktree root — parallel-collision is not Mission 1's problem).
- ❌ No queue-length / wait-time instrumentation (parallel-readiness signals — out of scope).
- ❌ No multi-agent coordination, knowledge-base sharing, self-replanning, audit manifest infrastructure beyond what `pipeline.state.json` already gives.
- ❌ No qwen / gemma / local-model arm exploration (NORTH-STAR ops test #11 stays deferred).
- ❌ No cross-vendor / model-agnostic infrastructure work.
- ❌ No "skill description tuning to expand trigger surface." Description stays scoped to actual capabilities.

**What IS in scope during Mission 1**:
- Skill prompt + reference body refinement (BUILD/EVAL/CRITIC/DOCS/fix-loop quality).
- Mechanical gates that catch known failure classes (e.g. `spec-verify-check.py` pattern from iter-0019.6/.8/.9 — extend if measurement shows new categorical failure).
- Engine-routing decisions strictly as research, never as L2 product ship without L1 release-readiness first.
- Findings-schema enrichment when measurement shows the current rule_id vocabulary misses a real failure class.
- Subtractive cleanup of any skill prompt section that doesn't pull weight (Karpathy 4 + Subtractive-first).
- Single-worktree fix-loop convergence / wall-time / quality measurement.
- Real-project trial diagnostics with explicit before/after evidence.

**Mission 1 unblocks Mission 2 only when**:
- All 5 gates above hold on a paid 9-fixture L0/L1 (and optionally L2 if any L2 shape ships) suite.
- Real-project trial passes once (NORTH-STAR test #14 final stop condition).
- The L1 surface is documented and positioned as the canonical product (not "experimental").
- The asymmetry between harness and bare prompting is empirically clear (categorical reliability, not just average margin).

---

## 🚀 MISSION 2 (deferred — do NOT touch until Mission 1 unblocks) — Parallel-fleet readiness substrate

**Frame**: same single-task quality, but the user can run N≥5 simultaneous independent tasks hands-free with no per-task quality collapse, no crosstalk, and aggregate wall-time materially shorter than serial.

**Mission 2 is ONLY relevant after Mission 1 ships**. The reason: an N=5 fleet of marginally-better-than-bare agents collapses to zero ROI — the user is better off prompting bare 5 times. The fleet only earns its existence if Mission 1 has *already* delivered overwhelm-level single-task value to multiply.

### What's already designed for Mission 2 (ready to consume when Mission 1 unblocks)

Codex GPT-5.5 deep consult (2026-04-29, two rounds totalling ~260k tokens / xhigh) produced a complete substrate design. Preserved here as historical record so Mission 2 doesn't re-derive:

**Core primitive**: `git worktree`-per-task. Repo already has `.gitignore:9 .claude/worktrees/` so the foundation is partial.

**iter sequence (Mission 2)**:
1. **Worktree substrate** — `--worktree` flag on auto-resolve creates per-task worktree at `.claude/worktrees/<run_id>/` from a captured `fleet_base_sha`. Stages `.claude/skills`, `.claude/settings.json`, `CLAUDE.md` into the worktree (Codex Q1 — runtime files don't carry through `git worktree add` automatically). Records `{worktree_path, branch, base_sha, parent_repo}` in pipeline state. Dirty-base policy: block uncommitted changes OR explicit copy. External audit at `~/.devlyn/runs/<repo-hash>/<run_id>/manifest.json` (the worktree-local `.devlyn` is gitignored and disposable, so audit must live outside).
2. **Resource leases** (SQLite-backed at `$(git rev-parse --git-common-dir)/devlyn/resources.sqlite` or global `~/.devlyn/resources.sqlite`):
   - `git-worktree-admin` — non-fungible cap 1 (because `git worktree add/remove/prune` touches shared git admin metadata).
   - `dev-server-port` — fungible pool 5173-5199 with FIFO waiters.
   - `provider-anthropic` — adaptive queue/backoff (NOT default `C=1`; would destroy the fleet goal).
   - `codex-session` — explicitly NOT added unless `~/.codex/sessions/<DAY>/` corruption is empirically proven (Codex Q1-rev: a global codex mutex destroys fleet value).
   - Locks held only during the narrow phase that needs the resource. Never across whole run.
   - Locking primitive: Python `fcntl`/`flock` advisory (NOT shell `flock` — macOS doesn't ship it; evidence at `pilot-claude-strict-n1.json:59`).
   - Stale-lease cleanup based on owner pid liveness + heartbeat expiry (OS locks release on crash; PID/mkdir locks have zombie risk).
3. **N=5 paid smoke** — first meaningful parallel measurement. Skip N=2 paid (per Codex Q4-rev: N=2 acceptance is meaningless against the user's 5-10 floor). Cheap N=2/3 synthetic canary OK for crosstalk detection.
4. **N=10 paid smoke + queue metrics**.
5. **Synthetic high-N stress** with queue length / wait time exposed; only then claim NORTH-STAR ops test #15 axis.

**No global N cap**. Per user directive 2026-04-29: harness must scale without imposing a ceiling. Resources queue, not refuse. The harness must EXPOSE queue length + wait time so the operator can detect when arrival rate exceeds resource service rate ("queueing collapse") — but harness does not pre-emptively cap.

**Operator vs harness responsibility split** (Codex Q2-rev):
- Operator/fleet config owns: machine size, `ulimit -n`, `kern.maxprocperuid`, API tier, spend cap, disk budget, package-manager cache strategy.
- Harness owns: detect pressure, classify it, queue where queueing is possible, retry 429s with adaptive backoff, release leases, reap stale children, avoid turning capacity failures into fake task failures.

**Cleanup protocol mandatory from day 1** (Codex Q3-rev): per-run manifest with status lifecycle, `git worktree remove` instead of `rm -rf`, dirty-worktree protection, TTL/dry-run prune, branch namespace cleanup, `git worktree prune` under the same git-admin mutex.

**Cheap quick-win discovered for Mission 2** (Codex Q3 / consult 1): `codex exec --ephemeral` exists in the local CLI. Auto-resolve should pass it on Codex calls that don't need session resume — eliminates the `~/.codex/sessions/` shared-write concern at zero cost. Can be applied during Mission 1 if it doesn't change behavior, but the parallel safety it gives is a Mission 2 prerequisite.

**Bench harness (`run-fixture.sh` cp -R isolation, `/tmp/bench-<run_id>-<fixture>-<arm>`) stays as-is** during Mission 2 (Codex Q4 consult 1). Only the production `/devlyn:auto-resolve` path migrates to `git worktree`. Switching bench risks the load-bearing measurement infrastructure.

**Biggest risk to manage in Mission 2** (Codex Q9 consult 1): "mistaking workspace isolation for fleet readiness." Worktree solves file/index/state collisions but NOT skill staging, dependency hydration, global CLI state, API quotas, browser/process resources, or merge composition. Mission 2 must measure these as separate axes, not assume worktree subsumes them.

---

## 🌐 MISSION 3 (deferred — long-horizon, do NOT scope until Mission 2 unblocks) — Autonomous AI Agent organisation

**Frame**: the harness composes into a pyx-style autonomous organisation. Multiple agents cooperate (not just run isolated in parallel) on shared knowledge bases, hand off sub-goals, re-plan when stuck, and produce auditable trails the human can trust without per-task supervision.

**Mission 3 is the user's stated ultimate goal** (NORTH-STAR.md "The ultimate goal" section). It is *not* immediate work. It is the destination that justifies why Missions 1 and 2 must be done correctly.

### Open architecture questions for Mission 3 (record-only — do NOT design yet)

Codex GPT-5.5 verdict 2026-04-29 (Q6 ultimate-goal consult) flagged four axes Mission 1 + 2 do not yet operationalise:

1. **Inter-agent coordination** — shared knowledge base, shared design decisions, shared test infrastructure. Cooperative agents sharing state before isolation is stable will amplify failures (Codex Q6 / consult 1: build isolated agents first, cooperative agents later).
2. **Self-direction / re-planning** — does an agent decide when its current task is unsalvageable and switch sub-goal autonomously?
3. **Failure containment** — when one of N agents goes off-rails, does the failure stay contained, or does it taint other agents' outputs / shared repo state?
4. **Audit / accountability** — humans need a trail to trust a hands-free organisation. The Mission 2 manifest design (`~/.devlyn/runs/.../manifest.json`) is the seed; Mission 3 extends it with cross-agent dependency graphs, decision-trace lineage, and human-readable summaries.

These are recorded so they don't get re-discovered each session. They bind nothing now.

---

## How to use this file

1. **Every iter file's "Why this iter exists" section names which Mission it serves.** If it does not, reject the iter scope per Pre-flight 0.
2. **No iter touches a Mission 2 or Mission 3 surface during Mission 1** — even if the work is "small" or "would be nice." That is scope creep per Goal-locked execution (CLAUDE.md). Surface as a Mission 2/3 note, do not implement.
3. **When Mission 1 unblocks, this file is updated**: Mission 1 → "✅ COMPLETED <date>" + summary, Mission 2 → "🎯 active." HANDOFF rotates accordingly.
4. **Mission boundaries are hard, not soft**. The 5 hard NOs in Mission 1 are not preferences. Skipping one is a violation.
