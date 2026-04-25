# 0004 — Variant subprocess MCP/config isolation

**Status**: SHIPPED (partial — outer isolation only; inner codex isolation follows in iter 0005)
**Started**: 2026-04-25
**Decided**: 2026-04-25

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

Two runs against F7 with the new outer-MCP isolation:

| Run | Timeout | Variant elapsed | Variant transcript | Variant diff | Variant verify | Score | Margin |
|---|---|---|---|---|---|---|---|
| iter-0004 fastrepro | 300s | 301s (timeout) | 0 bytes | **1904 bytes** (uncommitted) | 5/6 | 98 | +2 |
| iter-0004 f7 (real) | 1200s | 1201s (timeout) | 1 byte (newline) | **0 bytes** | 3/6 | 68 | −29 |

**Both runs hit the watchdog** even though the outer Claude `claude -p` subprocess no longer loaded user MCP plugins (verified: claude-debug.log shows no user MCP activity). The hang did not move to "claude can't start" — it moved to "claude starts fine but the inner `codex exec` it spawns hangs."

Codex round 4 traced the real-subset hang to **two pending LocalShellTask processes at watchdog kill time**:
1. `bw0nyvsax` — backgrounded `codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check ...` for BUILD phase. Output file stayed at 0 bytes for the entire 10+ minutes it ran.
2. `bqwgajc1e` — `tail -f` monitor watching task #1's empty output. Naturally also hung.

The fastrepro run happened to launch `codex exec` foreground (`| tail -200`) and the watchdog killed codex while it was actively writing files, so partial work survived in the working tree (1904 bytes of uncommitted changes). The real run launched it backgrounded, and codex emitted zero bytes the whole time, so killing it produced no work product.

Bare arms across both runs: stable at score 96–98, ~40s wall, no regression.

`pipeline.state.json` schema drift between runs (`engine: auto` vs `engine: codex`, `phases: {…}` vs `phases: {}`) is a tell that the auto-resolve skill is *prompt-driven* — claude rewrites that file each turn, so the schema reflects whatever the model chose to write rather than a deterministic code path. Not a code bug; it's how skill orchestration works.

## Lessons

1. **Outer MCP isolation is necessary but insufficient.** Adding `--strict-mcp-config --mcp-config '{"mcpServers":{}}'` to the harness's outer `claude -p` keeps user-level MCP plugins out of Claude Code itself. But it does NOT propagate to the inner `codex exec` subprocess, which loads its own user-level config (`~/.codex/config.toml` — operator has `[mcp_servers.pencil]` declared). The MCP race shifted location, not severity.

2. **The real F7 blocker is inner Codex MCP race + a backgrounded shell pattern.** Inner `codex exec` initialization stalls when racing user-level MCP servers (same root-cause class as iter 0003's misdiagnosis, but at a different process layer). Combined with claude orchestrator backgrounding the call and waiting on a `tail -f` monitor, the variant arm sits silent for 10+ minutes producing nothing.

3. **The `claude -p` "0-byte transcript" symptom in iter 0003 was misleading.** It conflated three separate possibilities: (a) Claude Code itself hung (iter 0003's first guess), (b) Claude Code worked but didn't flush transcript until end-of-session, (c) Claude Code worked but its child `codex exec` hung. The iter-0004 fastrepro showed (b) holds (transcript empty, but actual work in the work tree); the iter-0004 real run showed (c) is the dominant blocker.

4. **`--debug-file` + reading the project JSONL is the right diagnostic level.** The 0-byte transcript would have hidden everything. The debug-file showed API request gaps; the project JSONL identified the exact LocalShellTask command and its 10-minute zero-byte runtime. Without these we'd have iterated blind.

5. **Do not trust pipeline.state.json schema for cross-run comparison.** It's hand-written by the model at runtime. Differences between runs reflect model choice, not code drift.

6. **Refined hypothesis (becomes iter 0005):** add `--ignore-user-config --ignore-rules --ephemeral` to every `codex exec` invocation in the skills (canonical: `_shared/codex-config.md` + the inline mention in `auto-resolve/references/engine-routing.md`). This forces inner Codex to a hermetic state matching what outer Claude already enforces. Predicted: F7 variant completes within 600–900s, transcript flushes, margin recovers to ≥+5.

## Decision

**SHIPPED (partial).** The outer-MCP isolation change is correct, low-risk, and removes a previously-uncontrolled source of variance even though it didn't fix F7 by itself. The change stays. Iteration 0005 follows immediately to address the remaining inner-codex layer, which round 4 traced as the actual F7 blocker.

The `--debug-file` flag added in this iteration is what made round 4's diagnosis possible. Keeping it on as standard harness instrumentation.
