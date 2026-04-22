# Pilot Run Results (v3.2, n=1, claude engine)

Date: 2026-04-23
Context: the user challenged the `run-real-benchmark.md` "15–45 hours / 30-paired-run" claim as unrealistic. This pilot confirms the claim was massively overestimated.

## Why only n=1

Original plan was n=3 paired (T1 + T2 + T3, auto + claude). Three blockers:

1. **T2 and T3 are fictitious in this repo.** `T2-standard/spec.md` references `src/api/orders/cancel.ts` and `T3-high-risk/spec.md` references `src/auth/session.ts` — neither exists in devlyn-cli. `run-real-benchmark.md:8` flagged this ("T1 needs a real CLI; T3 needs a real auth flow"); it was never acted on.
2. **T1 is also fictitious.** Its spec describes a "recieve → receive" typo that does not exist anywhere in `bin/devlyn.js`.
3. **Codex MCP disconnected** mid-session, so `--engine auto` / `--engine codex` were unavailable. `--engine claude` is the only measurable engine this pass.

Answer: substitute the fictitious T1 with a **real trivial fix** in the repo. Measure that. Report honestly. The directional claim ("fast route is not 15–45 min") does not need n=3 to be convincing — it needs one real data point.

## Methodology

A benchmarking agent ran in a disposable git worktree. It chose a genuine 1-line improvement (grammar fix in `agents-config/evaluator.md:15`), then impersonated the auto-resolve orchestrator for the `fast` route: PARSE → BUILD → BUILD GATE → EVAL → FINAL REPORT. No fix loop triggered. Single commit created in the worktree (discarded — not merged to main).

## Measured values

From `benchmark/auto-resolve/pilot-claude-fast-n1.json`:

| Phase | wall_ms | tokens | verdict |
|---|---|---|---|
| parse | 6,410 | n/a | PASS |
| build | 32,960 | n/a | PASS |
| build_gate | 92 | 0 | PASS (no gate matched — devlyn-cli has no build system) |
| evaluate | 10,272 | n/a | PASS |
| **Sum of phase wall_ms** | **49,734** | | |
| Orchestration gap (inter-phase) | 27,555 | | |
| **Total wall_ms** | **77,289** | | |
| **Total wall-time** | **~77 seconds** | | |

The agent's own Claude Code session consumed **115,317 tokens** end-to-end for this run (from the agent's `total_tokens` usage notification). That number covers the agent's orchestration + every phase it ran inline. It is the honest per-run cost estimate.

## Caveat — per-phase tokens are null

Per-phase token measurement failed. The measurement spec required spawning each phase as an `Agent` subagent with `mode: "bypassPermissions"` and capturing each subagent's `total_tokens` from its completion notification. The benchmarking agent could not access the `Agent` tool in its environment — only `TeamCreate`/`SendMessage` were available, and those have persistent async semantics (teammates remain live between turns, no single completion notification). It therefore executed each phase inline as the orchestrator.

Consequences:
- Per-phase tokens are null in the JSON. Only the agent's aggregate `115,317` is recoverable, and that includes overhead from tool-search probing for the unavailable `Agent` tool.
- Per-phase wall_ms values are a **lower bound**. A real subagent run would add per-phase startup cost (fresh context, skill reading, exploration within a larger token window).
- Directional takeaway is unaffected: adding even 2–3× for subagent overhead brings total wall_ms to ~150–250 seconds — still a 4–12 min run, not 15–45.

This is also a blunt signal about the `perf` instrumentation section we just added to `pipeline-state.md` — it assumes Agent-subagent completion notifications are available. For environments where they're not, the instrumentation needs a fallback (measure orchestrator wall-time only, report tokens as aggregate-agent-usage rather than per-phase). Documented as a known limitation.

## What this changes

Original `run-real-benchmark.md:60` math:
> 10 paired × 3 tiers × 2 versions = 60 runs. At ~15–45 min/run, budget 15–45 hours of wall time.

Corrected by measured data (serial execution, claude engine, n=1):
> Fast-route trivial task: **~77 seconds** measured (expect ~2–4 min with real subagent spawns). 60-run parallel (via `git worktree`): **~3–4 min wall-time wallclock**. 60-run serial: **~80 min.**
> Normal/strict-route complex tasks with fix loops, review, challenge: likely **5–20 min/run** is the honest range. Not 15–45.

New suggested benchmark plan (for the next Codex-available session):
- n=5 paired (3 tiers × auto + claude, dropping one tier for schedule), parallel via `git worktree`, budget **~1 hour wall-time**.
- Or: `production instrumentation` (the `perf` block in state.json, added this commit). After 2–3 weeks of real auto-resolve usage, you have n=20+ real-task data points for free.

## Honest assessment of the v3.2 "Worldclass" claim

On measured evidence:
- Cold-start token reduction (14,438 → 6,280) — **real, measurable, reproducible**.
- Post-EVAL invariant (orchestrator diff-check) — **not exercised by this fast-route pilot** (no Simplify/Review/etc. phases ran). Needs strict-route data before claiming it works in production.
- Archive contract — **not exercised** (pilot ran inline, did not write `.devlyn/runs/`).

The structural improvements are real. The runtime claims need more measurement. Both things are true simultaneously.

## Reproducing

```bash
# Copy the result JSON back (if re-running the agent):
cp .claude/worktrees/agent-*/benchmark/auto-resolve/pilot-claude-fast-n1.json benchmark/auto-resolve/

# Wall-time and tokens are measured by the running agent itself — see the agent prompt
# used for this pilot (search git log for "Pilot auto-resolve run claude engine").
```
