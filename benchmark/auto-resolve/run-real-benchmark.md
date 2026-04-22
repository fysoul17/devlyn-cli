# Running the Real-Pipeline Benchmark (manual, expensive)

This document describes how to measure the dynamic properties NOT captured by `measure-static.py` or `trace-route.py`: wall-time, real token consumption, fix-round convergence.

## Prerequisites

- Codex MCP server available (`/devlyn:auto-resolve` requires `--engine auto` for cross-model GAN dynamic).
- A representative git repository where the test cases are realistic (T1 needs a real CLI; T3 needs a real auth flow).
- Sandboxed execution per run — each run leaves commits and side effects; reset between runs.

## Procedure

For each tier × version pair:

1. **Create a sandbox worktree**:
   ```bash
   git worktree add /tmp/auto-resolve-bench-$(date +%s) <baseline-ref>
   cd /tmp/auto-resolve-bench-*
   ```

2. **Install the test spec** at the path the task references (e.g. `docs/roadmap/phase-1/1.1-cli-help-typo.md` from `test-cases/T1-trivial/spec.md`).

3. **Record start time + git sha**, then run the pipeline:
   ```bash
   time /devlyn:auto-resolve "$(cat test-cases/T1-trivial/task.txt)" \
     2>&1 | tee run-log.txt
   ```

4. **Capture actuals** to `test-cases/<tier>/actual.<version>.json`:
   ```json
   {
     "wall_seconds": <int>,
     "route_selected": "<fast|standard|strict>",
     "route_reasons": [...],
     "phases_executed": [...],
     "fix_rounds_used": <int>,
     "final_verdict": "<PASS|NEEDS_WORK|BLOCKED|MAX_ROUNDS_EXHAUSTED>",
     "criteria_verified": <int>,
     "criteria_failed": <int>,
     "findings_emitted_total": <int>,
     "findings_open_at_exit": <int>,
     "commits_created": <int>,
     "guardrails_bypassed": [...]
   }
   ```

5. **For token accounting**: enable per-subagent `usage` logging and sum across the run. Each `Agent` and `mcp__codex-cli__codex` call returns `total_tokens` — aggregate.

6. **Reset the worktree** and repeat for the other version:
   ```bash
   git worktree remove /tmp/auto-resolve-bench-<id> --force
   git worktree add /tmp/auto-resolve-bench-new HEAD
   # run again
   ```

## Statistical significance

For publishable numbers, run 10 paired runs per tier. Observed variance across LLM generations will typically be ±10-20% on wall-time. Token consumption is more stable (±5-10%) because routing decisions are deterministic.

10 paired × 3 tiers × 2 versions = 60 runs. At ~15-45 min/run, budget 15-45 hours of wall time.

## Grading parity

After collecting actuals, use `grade-parity.py` (not yet implemented — template below) to compare baseline vs head:

```python
# For each tier:
# - Assert: baseline.criteria_verified == head.criteria_verified (equivalence)
# - Assert: head.findings_open_at_exit == 0 (guardrail: no open blockers at exit)
# - Assert: head.fix_rounds_used <= baseline.fix_rounds_used + 1 (no significant regression)
# - Report: head.wall_seconds / baseline.wall_seconds (efficiency ratio)
# - Report: head.total_tokens / baseline.total_tokens (token ratio)
```

## Honest reporting

Numbers from these runs go into `BENCHMARK-RESULTS.md` under a new section "4. Dynamic measurements (real runs)" — not inline with hypotheses. Each number carries: test case, version, sample size, variance.

Until this procedure runs, the `BENCHMARK-RESULTS.md` file makes no claim about wall-time or token savings for v2.1.
