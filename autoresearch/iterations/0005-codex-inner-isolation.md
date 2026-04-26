# 0005 — Inner `codex exec` isolation (`--ignore-user-config --ignore-rules --ephemeral`)

**Status**: REVERTED (full-suite refutes ship eligibility)
**Started**: 2026-04-25
**Decided**: 2026-04-26

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

F7 subset (run-id `20260425T122105Z-1982db8-iter-0005-f7`):

| Signal | Predicted | Observed |
|---|---|---|
| variant transcript | NON-EMPTY (≥10KB) | **1588 bytes** (security-review CRITIC sub-pass output flushed at end-of-session) |
| variant elapsed | 600–900s | **664s** ✅ (precisely in range) |
| variant timed_out | false | **false** ✅ |
| variant invoke_exit | 0 | **0** ✅ (natural session exit) |
| LocalShellTask kills at end | 0 | **0** ✅ (no inner Codex hang) |
| API request count | normal pipeline (~30–60) | **60** ✅ |
| pipeline phases | build→build_gate→evaluate→critic | **build, build_gate, evaluate, critic** all completed |
| C1–C4 status | implemented/verified | **all 4 verified** ✅ |
| diff_bytes | positive | **2158** ✅ |
| files_changed | 2 | **2** (`bin/cli.js`, `tests/cli.test.js`) ✅ |
| variant verify | 5/6 | **5/6** (one `node --test` "unexpected_text" — same fail as fastrepro; bare also fails it) |
| variant score | high | **99** ✅ |
| F7 margin | ≥ +5 | **+3** ⚠️ (variant won, but ship-gate floor not crossed) |

Per-arm wall: variant **664s** / bare **36s**. Bare arm stable at 96 (matches prior runs).

Trajectory across iterations on F7:

| Iter | Variant transcript | Diff bytes | Variant score | Margin |
|---|---|---|---|---|
| 0003 (no isolation) | 0 | 0 | 56 | −42 |
| 0004 fastrepro (outer iso, 300s cap) | 0 | 1904 (uncommitted) | 98 | +2 |
| 0004 real (outer iso, 1200s) | 1 | 0 | 68 | −29 |
| **0005** (outer + inner iso, 1200s) | **1588** | **2158** | **99** | **+3** |

Cumulative improvement: −42 → +3 (+45 margin units across 3 iterations).

## Lessons

1. **Inner Codex hermeticization is the load-bearing fix.** Outer Claude isolation (iter 0004) was necessary preparatory work but did not move F7's margin — it just shifted where the leak was. The actual blocker was inner `codex exec` loading the operator's `~/.codex/config.toml` which declares `[mcp_servers.pencil]`. Fixing that closed the loop.

2. **`--ephemeral` matters for cross-run determinism.** Iter 0004's run-to-run variance (fastrepro got partial work, real subset got nothing) was likely tied to codex session state in `~/.codex/sessions/` that mutated between runs. Adding `--ephemeral` removes that as a possible source. We can't run the experiment to isolate which of the three flags carried the win, but they're all defensible per the same isolation principle, so the bundle ships together.

3. **Project-policy alignment matters.** `CLAUDE.md` and `_shared/codex-config.md` both say "MCP is not in the loop." Iter 0003–0005 traced what happens when policy is documented but not enforced at the actual subprocess boundaries. Now both layers (outer claude, inner codex) are flag-enforced. The policy and the runtime now agree.

4. **F7 margin +3 is likely the fixture's practical ceiling.** Bare arm scores 96, variant 99 — both produce essentially correct work; both miss the same `node --test` verify command on the same "unexpected_text" reason. Without redesigning F7, no skill change can pull more separation. The ship-gate threshold of +5 may be unrealistically tight for "stress" fixtures where bare-but-careful work is enough; that's a benchmark-design question for a future iteration.

5. **`pipeline.state.json` schema as health proxy.** A natural-completion run shows `phases: {build, build_gate, evaluate, critic}` and all criteria `verified`. A hung run shows `phases: {}`, criteria `pending`. Cheap diagnostic that doesn't require reading transcripts.

6. **Diagnostic flag (`--debug-file`) earned its slot.** Round 4's diagnosis of "two LocalShellTask hung" was only possible because per-arm debug-file existed. Keeping it on is good harness hygiene at near-zero cost.

## Full-suite outcome

The DEFER condition triggered the full suite (run-id `20260425T125125Z-ab15f60-iter-0005-full`, ~3h). Per-fixture margin vs `baselines/v3.7-final.json`:

| Fixture | v3.7-final | iter-0005-full | Δ | Wall(V/B) | Verify(V/B) | LocalShellTask kills | Transcript |
|---|---|---|---|---|---|---|---|
| F1 trivial | (small +) | **+9** | + | 172s/33s | 80%/80% | 0 | normal |
| F2 medium | **+12** | **−82** | **−94** | 1201s/126s | 16%/100% | **2** | 58B "Codex is running…" |
| F3 high-risk | (≈0) | **+3** | + | 1501s/55s | 75%/75% | (timeout) | (timeout) |
| F4 stress | **+14** | **+1** | **−13** | 924s/188s | 100%/75% | **0** | 2090B |
| F5 stress | **+16** | **−35** | **−51** | 1501s/41s | 40%/80% | **1** | 0B |
| F6 stress | (≈+7) | **+3** | −4 | 1496s/65s | 83%/83% | **1** | 0B |
| F7 stress | **−12** | **+3** | **+15** | 346s/38s | 83%/83% | **0** | 2020B |
| F8 edge | **+32** | **+27** | −5 | 904s/39s | 80%/80% | **1** | 1571B |
| F9 e2e | **+24** | **+7** | **−17** | 1805s/79s | 20%/40% | (natural) | (natural) |

**Suite avg margin: +10.6 → −7.1.** −17.7-point regression. Ship-gate **2/8 fixtures ≥ +5** (need 7/9). FAIL.

F7 is the only fixture that genuinely improved (the iteration's named target). Every other fixture regressed by ≥4 points, including F4 / F9 which had **zero** LocalShellTask kills and natural exits — so the regression is not solely the orchestrator-background pattern; the iter 0005 flags appear to materially shift codex's behavior even on clean runs.

## Lessons

1. **Subset positive ≠ full-suite positive.** The F7 subset cleanly confirmed the hypothesis (margin −42 → +3, transcript flushed, 0 leaks, all phases ran). Yet the full suite refuted ship eligibility outright. The playbook's DEFER rule earned its place — without the full-suite gate, this would have shipped a 17.7-point regression.

2. **The "0 LocalShellTask kills" oracle is not sufficient on its own.** F4 and F9 both ran cleanly (0 kills, natural exit) and still regressed by 13 / 17 points respectively. That points at iter 0005's flags changing model behavior in subtle ways — possibly via codex losing the project trust state from `~/.codex/config.toml` (`[projects.…trust_level=trusted]` entries) which then makes codex more conservative on every operation, not just MCP-affected ones.

3. **The F2/F5 collapse is dominated by a different root cause: orchestrator background-launch pattern.** F2 transcript captured this verbatim: *"Codex is running. I'll wait for completion notifications."* Then Stop fires, but the backgrounded `codex exec` + `tail -f` monitor never return. The watchdog kills both LocalShellTask processes at metadata.timeout. iter 0005 did NOT fix this — it isolated codex but didn't change the orchestrator's choice to background it.

4. **My initial pattern-match ("0 kills explains everything") was too clean.** Codex round 5 caught it: F4 with 0 kills still regressed materially. I was selectively confirming. The honest read is "iter 0005 is not proven to be the direct cause of the full regression, but it is absolutely not acceptable as the new baseline."

5. **Refined hypothesis (becomes iter 0006):** add an explicit "foreground-only" execution contract to `_shared/codex-config.md` and `auto-resolve/references/engine-routing.md`. Skills must run `codex exec` as a foreground command, stream output, wait for exit. No `&`, no `tail -f`, no `run_in_background`, no `Monitor`/`TaskOutput` as the wait path. This addresses the F2/F5 collapse class directly. The iter 0005 flags themselves are deferred — re-add only if a future iteration measurably needs them, separately from this fix.

6. **Watchdog classification bug discovered (separate concern):** when watchdog fires shortly *before* `metadata.timeout_seconds` (e.g., F6 elapsed 1496s vs timeout 1500s), result.json marks `timed_out: false` + `invoke_exit: 124` + `invoke_failure: true`. Misleading — the run was killed by our wall-clock guard but doesn't appear so in the structured record. File as a small harness-correctness fix, separate from iter 0006.

## Decision

**REVERT.** The change is undone in `_shared/codex-config.md` (canonical) and `auto-resolve/references/engine-routing.md` (inline). The iteration file stays as institutional history; the diff returns to the iter 0004 SHIPPED state.

Codex round 5 framed it precisely: *"correct sub-fix inside a failing integrated run is not a ship decision."* Even granting that the regression source is more orchestrator than the flags themselves, the playbook is unambiguous — full-suite gate is the ship gate, and a 17.7-point swing well outside any plausible noise envelope refutes ship eligibility.

The single legitimate win on F7 stays as evidence that inner-codex isolation matters in some form. It just needs to land alongside (or after) iter 0006's foreground-only contract, in a state that doesn't regress F2/F4/F5/F9.

Follow-on: **iter 0006 — foreground-only codex execution contract** (file follows in next commit). Falsification gate before any further full suite: F2 alone, then F5, then full suite only after both recover.
