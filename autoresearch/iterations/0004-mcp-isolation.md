# 0004 — Variant subprocess MCP/config isolation

**Status**: PROPOSED
**Started**: (not yet)
**Decided**: (not yet)

## Hypothesis

The F7 variant `claude -p` subprocess hangs because Claude Code, on startup, loads every MCP plugin in the operator's user-level config (pencil, codex-cli, telegram, vercel, claude-in-chrome, …). One of these plugins races, blocks, or simply takes too long under accumulated session load, and claude never produces a single byte of transcript before the watchdog kills it at T+1200s. Adding `--strict-mcp-config --mcp-config '{"mcpServers":{}}'` to **both** benchmark arms' `claude -p` invocation forces an empty MCP set in the subprocess only — skills still resolve via `/skill-name`. The harness becomes hermetic w.r.t. user MCP. Predicted: F7 variant produces a non-empty transcript, completes well under timeout, and recovers margin per iteration 0002's intent.

This iteration replaces the predecessor draft (`0004-codex-mcp-reap.md`, orphan-reap hypothesis), which codex round 3 falsified by pointing out (a) F6/F7 asymmetry is not route-driven (F6 actually used codex due to the `crypto` keyword), (b) "MCP race" was the wrong level of fix when our skills don't even use MCP, (c) the right level is isolating the subprocess from user-level MCP entirely.

## Mechanism

Why-chain (continues from 0003's chain, replacing the old #7-12 with codex round 3's correction):

7. Why does the F7 variant produce 0 bytes of transcript before the watchdog fires? → The subprocess never reaches first model output. It is blocked somewhere during init.
8. Why is it blocked at init? → `claude -p` loads every plugin in the operator's user-level Claude Code config on startup. The user has many MCP plugins installed (pencil, codex-cli, telegram, claude-in-chrome, vercel-plugin, plus skills providers). Plugin init is sequential / partially blocking.
9. Why does F6 not block but F7 does? → It is not a property of F7's spec or route. F6 happened to win the timing on prior runs; F7 happened to lose it. The block is environmental (operator-level MCP state at the moment of subprocess start), not fixture-level.
10. Why don't our skills *need* any user-level MCP? → Project policy (CLAUDE.md, `_shared/codex-config.md`) explicitly states "MCP is not in the loop. Skills shell out to `codex exec` CLI." So the variant arm subprocess loading user MCP is *strictly waste* — neither correctness nor capability depends on it.
11. Why is harness-level the right place to enforce that policy? → The benchmark is a controlled experiment. User MCP is uncontrolled environment, not an experimental variable. Hermeticizing the subprocess is what the fair-comparison principle demands.
12. Root: enforce empty MCP config on every `claude -p` the harness owns. Fix at level 12 — `--strict-mcp-config --mcp-config '{"mcpServers":{}}'` on both arms in `run-fixture.sh`.

Concretely confirmed by smoke test (pre-iteration): the flag combo runs in ~30s with `EXIT=0` and a "Hi" response when given `claude -p "Say hi" --dangerously-skip-permissions --strict-mcp-config --mcp-config '{"mcpServers":{}}'`. The mcp-server schema is `{"mcpServers":{...}}`, not raw `{}` (which fails validation). Documenting the schema in the iteration file so future readers don't repeat the round-trip.

## Predicted change

- F7 variant transcript: 0 bytes → ≥10 KB.
- F7 variant elapsed: 1201s (timeout) → 600–900s typical.
- F7 margin: −42 → ≥+5 (recovers iteration 0002's intent).
- F6 (already passing): no regression. May see minor wall-time reduction if F6's variant was also paying MCP-init cost.
- Bare arms (all fixtures): wall time unchanged or slightly faster. No score change.
- `claude-debug.log` per arm contains no user-MCP plugin activity. (Verification of "isolation actually took effect", per codex round 3's success criteria.)
- Suite reliability: full 9-fixture suite completes within 4–6 hr envelope every time.

## Diff plan

`benchmark/auto-resolve/scripts/run-fixture.sh` — extend both arms' `claude -p` invocation:

- Add `--strict-mcp-config --mcp-config '{"mcpServers":{}}'` (forces empty MCP).
- Add `--debug-file "$RESULT_DIR/claude-debug.log"` (per-arm debug log so the next hang has a location, not a guess).
- No other changes to the watchdog or surrounding logic — the 0003 process-group watchdog stays intact as the safety net.

NOT in this diff (deliberately deferred):
- `--output-format=stream-json` — would change the transcript contract; introduces a second hypothesis. (codex round 3, principle #1.)
- `--ignore-user-config` on inner `codex exec` calls inside skills — only add if 0004 fails and debug logs point at codex CLI as the new bottleneck.
- `--bare` — claude help warns it disables OAuth/keychain auth; would risk breaking authentication entirely. (codex round 3 explicitly counter-recommended.)
- Inline orphan-reap of stale processes — wrong level of fix (0004's predecessor draft, falsified by codex round 3).

## Principles check (provisional, finalized after run)

| # | Principle | Status | Evidence |
|---|---|---|---|
| 1 | No overengineering | (provisional ✅) | ~6 lines added to run-fixture.sh (2 flag-pair additions × 2 arms + minor formatting). No new files. |
| 2 | No guesswork | ✅ | Hypothesis specifies metric (F7 variant transcript bytes; margin) + mechanism (user-MCP load blocks startup) + direction. Smoke test pre-confirmed flag syntax. |
| 3 | No workaround | ✅ | Fixes the issue at the level the project policy already declared ("MCP is not in the loop"). Harness was leaking user MCP into the experiment; this enforces what the policy already says. |
| 4 | Worldclass production-ready | (filled after run) | |
| 5 | Best practice | (filled after run) | |

## Actual change

(filled after run)

## Lessons

(filled after run)

## Decision

(filled after run)
