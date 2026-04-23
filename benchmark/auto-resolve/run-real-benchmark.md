# Running the Real-Pipeline Benchmark

This document describes how to measure the dynamic properties NOT captured by `measure-static.py` or `trace-route.py`: wall-time, real token consumption, fix-round convergence.

**Measured baseline exists.** See `PILOT-RESULTS-v3.2.md` (n=1, claude engine, fast route) — one real run with honest numbers. Below uses those numbers to set realistic expectations for anyone planning a larger run.

## The test cases in `test-cases/` are fictitious

`T1-trivial`, `T2-standard`, `T3-high-risk` describe specs that do not match the `devlyn-cli` codebase:
- T1 references a `"recieve"` typo in `bin/devlyn.js` that does not exist.
- T2 references `src/api/orders/cancel.ts` which does not exist.
- T3 references `src/auth/session.ts` and `migrations/` which do not exist.

The specs are useful for `trace-route.py` (static routing verification) but NOT for real pipeline execution. To run a real benchmark you need one of:
1. A representative repo where the test cases are realistic (e.g., port T2 to a Next.js e-commerce starter, T3 to a real auth library).
2. Substitute each test case with a genuine equivalent task in whatever repo you're in.
3. Skip scripted tests entirely and rely on `state.perf` data from real auto-resolve runs (production-as-benchmark).

Option 3 is the cheapest and produces realistic data — see "Production instrumentation" below.

## Prerequisites

- Local `codex` CLI on PATH if you want to measure `--engine auto` (cross-model GAN via `codex exec`). Without the CLI the harness silently downgrades to `--engine claude`; you can also force that baseline explicitly.
- A representative git repository — see note above about fictitious test cases.
- Disposable worktrees via `git worktree add /tmp/bench-$(date +%s) HEAD`. Each run leaves commits and side effects; use worktrees so they don't pollute the main tree.

## Procedure per paired run

1. **Create a sandbox worktree**:
   ```bash
   git worktree add /tmp/auto-resolve-bench-$(date +%s) HEAD
   cd /tmp/auto-resolve-bench-*
   ```

2. **Install the test spec** at the path the task references (e.g., `docs/roadmap/phase-1/1.1-cli-help-typo.md` from a real, not fictitious, test case).

3. **Run the pipeline** and record start/end + state.json:
   ```bash
   time /devlyn:auto-resolve "$(cat test-cases/<tier>/task.txt)" 2>&1 | tee run-log.txt
   ```
   At run end, `.devlyn/runs/<run_id>/pipeline.state.json` contains `perf.{wall_ms, tokens_total, per_phase[]}` — the measurement lives IN the artifact.

4. **Reset the worktree and repeat** for the other engine:
   ```bash
   git worktree remove /tmp/auto-resolve-bench-<id> --force
   git worktree add /tmp/auto-resolve-bench-new HEAD
   # re-run with --engine claude (or whichever engine you didn't just run)
   ```

## Statistical significance

Measured variance is small enough that n=3 paired gives useful directional signal. n=10 paired is publishable-quality but overkill for most decisions.

| Goal | Suggested n (paired per tier) | Tiers | Runs total | Engines | Wall-time (parallel via worktree) |
|---|---|---|---|---|---|
| Smoke check | 1 | 1 (fast) | 2 | auto + claude | **~2-4 min** |
| Directional | 3 | 3 (fast + standard + strict) | 18 | auto + claude | **~20-40 min** |
| Publishable | 10 | 3 | 60 | auto + claude | **~1-2 hours** |

These numbers use `git worktree` to run in parallel. Serial execution takes roughly the number of runs × longest-tier duration.

## Corrected wall-time per run (from pilot measurement)

Original version of this document said "15-45 min/run". That was wrong by 10-30×. Actual measured values (claude engine, `PILOT-RESULTS-v3.2.md`):

| Route | Measured (n=1) | Projected (with real subagent overhead) |
|---|---|---|
| `fast` (trivial, 0 fix rounds) | 77 s | 2-4 min |
| `standard` (medium, 0-1 fix rounds) | not yet measured | 4-8 min est. |
| `strict` (complex + team-review + security) | not yet measured | 8-15 min est. |

Fix-round convergence adds ~1.5-3× wall per extra round. A typical `max_rounds=4` run with 2 rounds used is still under 15 min for most real tasks.

**Token cost**: agent aggregate was ~115k tokens for the n=1 fast-route pilot. Extrapolating by phase-count, expect:
- fast: ~80-150k tokens/run
- standard: ~200-400k tokens/run  
- strict: ~500k-1M tokens/run (team + security dual-model phases multiply)

These are rough orders of magnitude — real data accumulating in `.devlyn/runs/<run_id>/pipeline.state.json:perf` will sharpen them over time.

## Token accounting

Each subagent returns `total_tokens` in its completion notification. The orchestrator captures it per phase into `state.perf.per_phase[].tokens`. Codex calls report `input_tokens + output_tokens + reasoning_tokens` in their response. For Dual-model phases (security_review on `--engine auto`), record both models' tokens as two separate `per_phase` entries so costs are separately recoverable.

At PHASE 8 the orchestrator sums per-phase into `state.perf.tokens_total` and archives `state.json` into `.devlyn/runs/<run_id>/`. Multiple runs in the same worktree leave a history — compare across them directly.

Note: if the runtime environment doesn't expose a way to capture subagent completion notifications (some benchmarking envs don't), per-phase tokens end up `null`. In that case the agent's own aggregate `total_tokens` is the only recoverable number. This is what happened in `pilot-claude-fast-n1.json` — documented there as a known limitation.

## Grading parity

For an auto-vs-claude paired comparison, grade on these axes:

```
# For each tier:
# - Assert: both runs' criteria_verified are equal (equivalence of outcome)
# - Assert: head.findings_open_at_exit == 0 (no blockers left at exit)
# - Assert: head.fix_rounds_used <= baseline.fix_rounds_used + 1 (no regression)
# - Report: head.wall_seconds / baseline.wall_seconds (wall-time ratio)
# - Report: head.total_tokens / baseline.total_tokens (token ratio)
```

A ratio of ~1.0 across wall-time and tokens means "auto and claude are indistinguishable in cost" — a legitimate outcome that would argue for simplifying to single-engine. A ratio < 1.0 on wall-time with ratio > 1.0 on tokens is the expected "auto is faster per unit work but costs more in raw tokens" — tradeoff to be evaluated.

## Production instrumentation (cheapest path to real data)

The `state.perf` block populates on every auto-resolve run automatically. After a few weeks of real use you have n=20+ real-task data points at zero additional cost. Query:

```bash
# All runs' perf blocks
for f in .devlyn/runs/*/pipeline.state.json; do
  jq '{run_id, engine: .engine, route: .route.selected, wall_ms: .perf.wall_ms, tokens: .perf.tokens_total}' "$f"
done
```

For per-phase breakdown:

```bash
jq '.perf.per_phase[] | {phase, engine, wall_ms, tokens, round}' .devlyn/runs/<run_id>/pipeline.state.json
```

This is how you get honest benchmark data without scheduling a dedicated benchmark window.

## Honest reporting

Numbers from these runs go into `BENCHMARK-RESULTS-v3.md` under a "dynamic measurements" section — not inline with hypotheses. Each number carries: test case, version (git sha), sample size, variance (where n >= 3), engine, route, fix rounds used.

Until a run produces real numbers, claims about wall-time or token savings from `--engine auto` vs `--engine claude` stay labeled as hypotheses.
