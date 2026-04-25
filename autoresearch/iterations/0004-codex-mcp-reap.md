# 0004 — Codex MCP race: pre-arm reap of stale codex-mcp-server processes

**Status**: PROPOSED
**Started**: (not yet)
**Decided**: (not yet)

## Hypothesis

Reaping lingering `codex-mcp-server` processes (and any other narrowly-whitelisted leaked Codex/MCP plugin processes from prior Claude Code sessions) immediately before each variant arm is invoked will let the inner `codex exec` calls (auto-resolve BUILD/EVAL/CRITIC) initialize their MCP layer cleanly. F7's variant arm — which produced 0 bytes of transcript across the full 1200s budget under iteration 0003's watchdog — will then actually run, implement the spec, and recover margin to ≥+5 (matching iteration 0002's predicted F7 outcome that was invalidated by this same race).

## Mechanism

Why-chain (continues from iteration 0003's chain, levels 7+):

7. Why did the watchdog cap the F7 variant at 1201s with empty transcript? → claude was hung on its first MCP-server-init handshake, before producing a single line of stdout/stderr.
8. Why is the handshake hanging? → codex CLI is the inner mechanism that auto-resolve invokes for BUILD/EVAL phases. codex CLI initializes an MCP layer; if a stale `codex-mcp-server` process from a prior Claude Code session is bound to the expected stdio/socket, the new init blocks on a handshake that the stale server can't service.
9. Why are stale codex-mcp-server processes around? → Other Claude Code MCP plugins and prior `codex exec` invocations leak children when their parent shells exit. macOS does not aggressively reap orphaned PPID=1 processes; they accumulate over a long Claude session.
10. Why don't we blanket-kill all `codex-mcp-server` processes? → Some belong to OTHER live Claude Code MCP plugins. Blanket-killing breaks them. Per the `devlyn:reap` skill's design, only a conservative whitelist (PPID=1 orphans matching narrow process-name patterns, owned by the same UID, untouched for ≥N minutes) is safe to reap.
11. Why is pre-arm the right level vs. mid-pipeline retry inside auto-resolve? → A retry-inside-the-skill pushes orchestration complexity into a place that should stay deterministic. The race is a benchmark-environment problem (fresh subprocess per arm), so it gets a benchmark-environment fix.
12. Root: stale orphan reap at arm boundary. Fix at level 12 — before each variant arm runs in `run-fixture.sh`, invoke the same conservative-whitelist reap pattern that `devlyn:reap` uses interactively.

## Predicted change

- F7 variant transcript: 0 bytes → non-empty (≥10 KB of pipeline output).
- F7 variant elapsed: 1200s (timeout) → 600–900s (typical auto-resolve completion).
- F7 margin: −42 → ≥+5 (recovers iteration 0002's predicted outcome).
- Other fixtures: unchanged on the bare arm; on the variant arm, a small wall-time reduction if any of them were also slow-starting due to the same race. No score regression.
- Suite reliability: full 9-fixture run completes within the advertised 4–6 hr envelope every time, no fixture's variant arm hits the watchdog.

## Diff plan

`benchmark/auto-resolve/scripts/run-fixture.sh`: add a pre-arm reap step immediately before the watchdog-bounded `claude` invocation, gated to the variant arm (bare arm doesn't invoke codex). Reap pattern:

- Conservative whitelist: process-name matches `codex-mcp-server`, PPID=1, same UID as the script, etime ≥ 300s (so we don't kill a server that's actively starting up for an in-flight Claude Code session elsewhere).
- Iterate process list via `ps -eo pid,ppid,uid,etime,comm` (portable on macOS + Linux).
- Send SIGTERM, wait briefly, SIGKILL stragglers.
- Log reaped PIDs to `$RESULT_DIR/reap.log` as evidence.

Optional follow-up if the narrow whitelist isn't enough: shell out to `claude --skill=devlyn:reap` (or its non-interactive equivalent). Not in the initial diff — start with the inline whitelist and measure.

**Cross-check with codex before commit:** confirm the etime/PPID criteria don't accidentally clobber a server that belongs to a different active Claude Code session. The `devlyn:reap` skill description ("conservative whitelist of known leaks — never guesses on unknown processes") is the upper bound; we should not be more aggressive than it.

## Principles check (provisional, finalized after run)

| # | Principle | Status | Evidence |
|---|---|---|---|
| 1 | No overengineering | (provisional ✅) | ~20 lines of shell. No new files. Reuses run-fixture.sh's existing log dir. |
| 2 | No guesswork | ✅ | Single hypothesis: F7 variant transcript becomes non-empty. Direction + metric + mechanism all named. |
| 3 | No workaround | ✅ | Fixes the race at its actual level (orphan reap), not at a symptom level (longer timeout, restart loop). |
| 4 | Worldclass production-ready | (filled after run) | |
| 5 | Best practice | (filled after run) | |

## Actual change

(filled after run)

## Lessons

(filled after run)

## Decision

(filled after run)
