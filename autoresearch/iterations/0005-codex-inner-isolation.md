# 0005 — Inner `codex exec` isolation (`--ignore-user-config --ignore-rules --ephemeral`)

**Status**: PROPOSED
**Started**: 2026-04-25
**Decided**: (not yet)

## Hypothesis

Iteration 0004 isolated the outer `claude -p` subprocess from user-level MCP plugins but did not propagate the policy to the inner `codex exec` subprocess. Codex's user-level config (`~/.codex/config.toml`) declares `[mcp_servers.pencil]`, so every `codex exec` call from a skill loads the operator's MCP layer regardless of what the outer Claude is doing. Round 4's analysis of the F7 real-subset run identified this as the actual blocker: inner `codex exec` for BUILD ran for 10+ minutes producing zero bytes of output, then a `tail -f` monitor on it sat waiting until watchdog kill. Adding `--ignore-user-config --ignore-rules --ephemeral` to every `codex exec` invocation in the skills makes the inner subprocess hermetic, matching what the outer is already enforcing. Predicted: F7 variant completes within 600–900s, transcript flushes, margin ≥ +5.

## Mechanism

Why-chain (continues from iter 0004's chain):

13. Why does iter 0004's outer-MCP isolation not fix F7? → It scoped only the outer `claude -p` process. The inner `codex exec` subprocess that auto-resolve spawns for BUILD/FIX phases reads its own config from `$CODEX_HOME/config.toml`.
14. Why does that matter? → The operator's `~/.codex/config.toml` declares `[mcp_servers.pencil]`. When `codex exec` starts, it tries to spin up the pencil MCP server (or any MCP servers configured there). That init can block, race, or simply take long enough that combined with auto-resolve's pipeline overhead, BUILD never produces output before the outer watchdog fires.
15. Why isn't `command -v codex` enough? → Availability is fine. The hang is in MCP init *after* the binary starts.
16. Why does it hang for ≥10 minutes producing zero bytes? → Round 4 didn't pin this down; the artifacts only prove "stall is inside the inner codex subprocess, not why." The most plausible explanation is a stdio handshake against an MCP server that isn't responding, but it could also be model-side reasoning loops + slow generation. Either way, isolating from user MCP eliminates the most-plausible cause.
17. Why is `--ignore-user-config` enough? → Per `codex exec --help`: "Do not load `$CODEX_HOME/config.toml`; auth still uses `CODEX_HOME`." That skips MCP server declarations in the file entirely while keeping authentication usable.
18. Why also `--ignore-rules` and `--ephemeral`? → `--ignore-rules` skips user/project execpolicy `.rules` files (uncontrolled environment, same class of leak as MCP). `--ephemeral` skips persisting session files to disk (codex sessions accumulate state in `~/.codex/sessions/` — orthogonal to MCP but a legitimate inter-run state leak that explains some of iter 0004's run-to-run nondeterminism). All three are isolation tools; applying them together costs nothing extra and removes more uncontrolled environment from the experiment.
19. Root: every skill-issued `codex exec` must run hermetically. Fix at level 19 — update the canonical invocation in `_shared/codex-config.md` plus the inline mentions in `auto-resolve/references/engine-routing.md` (which is what auto-resolve's BUILD/FIX phases actually read).

## Predicted change

- F7 variant transcript: 0/1 bytes → ≥10 KB (`claude -p` flushes at end-of-session if session ends naturally instead of by watchdog).
- F7 variant elapsed: 1201s timeout → 600–900s typical.
- F7 margin: −29 (iter 0004 real) → ≥+5.
- F6 (already passing without this fix): no regression. May see minor wall-time reduction.
- Other fixtures' bare arms: unchanged (bare doesn't invoke codex).
- Other fixtures' variant arms: those that route through Codex BUILD (anything matching strict route, e.g., F3/F6 with risk keywords) get the same hermeticization for free.
- `claude-debug.log` per arm shows no LocalShellTask timeouts (no Bash subprocesses pending at end of session).

## Diff plan

Two files, surgical:

1. `config/skills/_shared/codex-config.md` — already updated as part of this iteration's commit. Both canonical invocations (read-only and workspace-write) now include `--ignore-user-config --ignore-rules --ephemeral`. Notes section explains the rationale per flag with a backreference to this iteration.

2. `config/skills/devlyn:auto-resolve/references/engine-routing.md` — the two inline `codex exec ...` defaults updated to match the new canonical. This is the file auto-resolve's BUILD/FIX phases read at runtime; if it disagrees with `_shared`, the LLM tends to follow whichever is closer to the action.

NOT in this diff (deliberately deferred):
- `devlyn:ideate`, `devlyn:preflight`, `devlyn:team-resolve`, `devlyn:team-review` inline `codex exec` mentions — none of these are on F7's path. They will be updated when their respective fixtures or iterations exercise them. (Karpathy "Surgical Changes": touch only what the goal requires.)
- Switching auto-resolve's BUILD phase from background `&` patterns to foreground `tail -120 |` — codex round 4 noted background was a contributing pattern in the bad run. But the model orchestrator chose that pattern; we can't reliably control it from a skill prompt without scope creep.

## Principles check (provisional, finalized after run)

| # | Principle | Status | Evidence |
|---|---|---|---|
| 1 | No overengineering | (provisional ✅) | Two file edits, ~10 lines added. No new files, no new infrastructure. |
| 2 | No guesswork | ✅ | Round 4 identified the exact blocker (inner `codex exec` 10-min zero-byte stall). Hypothesis specifies the metric (variant transcript + elapsed + margin) and the mechanism. |
| 3 | No workaround | ✅ | Fixes the bug at the level of what's actually leaking — inner Codex's user config. The flags are documented isolation primitives, not patches. |
| 4 | Worldclass production-ready | (filled after run) | |
| 5 | Best practice | (filled after run) | |

## Actual change

(filled after run)

## Lessons

(filled after run)

## Decision

(filled after run)
