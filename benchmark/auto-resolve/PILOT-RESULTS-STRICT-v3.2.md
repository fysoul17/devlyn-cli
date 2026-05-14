# Strict-Route Pilot Results (v3.2, n=1, claude engine)

> Archive note (2026-05-14): historical v3.2 strict-route pilot for the deleted
> `auto-resolve` route. This inline n=1 pilot is not current solo<pair evidence;
> use `npx devlyn-cli benchmark audit` and complete pair-evidence rows for
> current decisions.

Date: 2026-04-23
Baseline: v3.2 working tree (commits up through 52af266)

## Headline

**v3.2 post-EVAL invariant + archive contract: both confirmed working end-to-end.** Two real bugs discovered and fixed in follow-up commit.

## Methodology

A benchmarking agent ran in a disposable git worktree. It picked a genuine small refactor (extract hardcoded pipeline permissions + `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` env into a single `DEFAULT_PIPELINE_SETTINGS` constant in `bin/devlyn.js`). The task body naturally contained Stage-A risk keywords (`permission`, `env`) so strict routing was organic; `--route strict` was also passed as belt-and-suspenders.

The agent impersonated the auto-resolve orchestrator and ran all 11 strict-route phases inline. The CLEAN phase was deliberately instructed to violate the findings-only invariant (commit a real code change) so the orchestrator's invariant-check could be observed end-to-end.

## Measured wall-time

| # | Phase | wall_ms | verdict | findings |
|---|---|---|---|---|
| 1 | parse + preflight + route | 27,738 | PASS | — |
| 2 | build | 33,108 | PASS | — |
| 3 | build_gate | 5,513 | PASS | 0 (no buildables in this repo) |
| 4 | browser_validate | 0 | SKIPPED | no web files |
| 5 | evaluate | 25,426 | PASS | 0 |
| 6 | simplify (findings-only) | 21,231 | PASS_WITH_ISSUES | 2 |
| 7 | review (findings-only) | 26,112 | PASS_WITH_ISSUES | 1 |
| 8 | challenge (findings-only) | 26,618 | PASS | 1 |
| 9 | security_review (findings-only) | 15,007 | PASS | 0 |
| 10 | clean (findings-only, invariant test) | 57,700 | NEEDS_WORK | 2 |
| 11 | fix_loop (triggered_by=clean) | 24,973 | PASS | 0 |
| 12 | evaluate (round 2, triggered_by=fix_loop) | 27,701 | PASS | 0 |
| 13 | docs | 4,855 | SKIPPED_NO_CHANGES | — |
| 14 | final_report + archive | 34,403 | PASS | — |
| **Total** | **wall_ms** | **402,381** | **PASS** | |

**~6.7 minutes for full strict route + 1 fix round + re-EVAL.** Per route averages:
- fast (n=1): 77 s
- strict (n=1): 402 s = **5.2× slower** than fast — reflects 8 extra phases + fix round + re-EVAL

## Invariant test — end-to-end observation

CLEAN phase, by instruction, committed a 1-line code change (commit `3b36e82` deleting an unused `readline` import in `bin/devlyn.js:6`). The orchestrator then executed:

```bash
git diff --name-only 6ca00e9 -- ':!.devlyn/**'
# output: bin/devlyn.js
```

Detected non-empty diff in non-state-file territory → ran `git reset --hard 6ca00e9` → post-revert diff empty → emitted:
- `INV-0001` (`rule_id: invariant.post-eval-code-mutation`, severity HIGH) into `.devlyn/invariant.findings.jsonl`
- Preserved `CLN-0001` (`rule_id: hygiene.unused-import`, severity LOW) in `.devlyn/clean.findings.jsonl` (the legitimate finding CLEAN was supposed to raise)

Both findings routed to PHASE 2.5 fix loop with `triggered_by: "clean"`. Fix subagent re-applied the `readline` deletion legitimately in commit `83a1759`. Re-EVAL (round 2) returned PASS; both INV-0001 and CLN-0001 transitioned to `status: "resolved"`.

**Conclusion: the post-EVAL findings-only invariant — the #1 correctness claim of the v3.2 redesign — works end-to-end in a real execution.**

## Archive contract — observation

Archive directory was created as `.devlyn/runs/ar-20260422T233646Z-f62dde5b4706/`, containing 18 artifacts (pipeline.state.json, criteria.generated.md, 7 pairs of findings.jsonl + log.md, plus invariant.findings.jsonl and fix-batch.round-1.json). Move via `mv` was atomic. Prune-to-last-10 was a no-op (only 1 run present).

**Bug discovered**: `flock` failed on macOS. The original `pipeline-state.md#archive-contract` said `flock .devlyn/runs/.prune.lock` unconditionally, but macOS does not ship `flock` on default `$PATH`. For this single run it was safe to proceed lock-free (no concurrent archives), but the spec needs a platform-aware primitive.

## Bugs found in v3.2 and fixed in follow-up

### Bug 1 (HIGH, fixed): Invariant check did not exclude `.devlyn/**`

**Symptom**: The orchestrator writes `pipeline.state.json` between phases (phase verdicts, perf entries). Without an explicit pathspec exclusion, `git diff --name-only <pre_sha>` would have returned `.devlyn/pipeline.state.json` on every post-EVAL phase — a false positive the invariant would have treated as an illegal code mutation, triggering revert + fix loop.

**Fix**: All 6 places that reference the invariant diff now use `git diff --name-only <pre_sha> -- ':!.devlyn/**'`. Files: `SKILL.md` (post_eval_invariant block + 5 per-phase enforcement sections) and `pipeline-state.md` (invariant #6). Commit: see follow-up.

**Why this bug slipped through**: the spec assumed state.json writes happened "atomically between phases" — true in concept but the orchestrator's actual implementation writes mid-phase (at phase start to record `started_at`, mid-phase to record findings artifacts, at end to record verdict). Any of those writes would have tripped the invariant. The pilot found this in the first real strict run.

### Bug 2 (MEDIUM, fixed): Archive lock not portable to macOS

**Symptom**: `flock` is Linux-native (util-linux); macOS does not include it. Archive would fail at the flock step on macOS developer machines — meaning the prune-to-last-10 logic would never run and `.devlyn/runs/` would grow unbounded.

**Fix**: Archive contract now specifies platform-aware locking: `flock` on Linux, `shlock` on macOS or a Python `fcntl.flock()` fallback. On lock acquisition failure, skip pruning and continue (never block archive on lock contention).

## What this pilot DID NOT cover

- `--engine auto` or `--engine codex` (Codex MCP unavailable in this environment; Codex CLI was available but the goal was a clean claude baseline for strict route)
- Browser validate phase (no web files)
- Build gate with real buildables (devlyn-cli is a static-file npm package, no tsc/cargo/docker)
- Multi-round fix loops exhausting `max_rounds` (only 1 fix round triggered)

Those remain open for future pilots.

## Caveats

- n=1. Results are illustrative, not statistically significant.
- Per-phase tokens are null — the benchmarking environment had no Agent tool and therefore no subagent completion notifications. Agent's own aggregate was 131,906 tokens for the entire 6.7-minute run.
- Phases ran inline, not as spawned subagents. Real subagent spawns would add per-phase startup overhead (likely 5–30 s each). Extrapolated: strict route with real subagent spawns ~ 8–12 min.
- Wall-time includes the deliberate invariant-test overhead (~10 s for the deliberate commit + revert + fix round trigger). A clean strict run without invariant test would be ~40 s shorter.

## Reproducing

See `benchmark/auto-resolve/pilot-claude-strict-n1.json` for the full measurement JSON. The agent prompt used is recorded in the commit message of the pilot commit (search `git log` for "strict-route pilot").

## What changes next

Neither bug was shippable as-is — both are now fixed in the follow-up commit. After the fixes, v3.2 is genuinely verified on its two most correctness-critical features. The remaining open items (F11 stale benchmark citations, F12 full-paired auto-vs-claude runs) are follow-up work not gated on this pilot.
