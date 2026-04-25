# HANDOFF — for the next session

**Read this first** in any new conversation that wants to continue the AutoResearch loop. It's the smallest set of pointers that lets you (or a future LLM) pick up exactly where we are.

---

## Current state of the harness

**Branch**: `benchmark/v3.6-ab-20260423-191315` (all iteration commits live here, not yet merged to main).

**Last shipped iteration**: 0003 (run-fixture.sh process-group watchdog — harness infra; F7-recovery prediction refuted, queued as 0004). 0002 (F6/F7 spec annotation) before that. DECISIONS.md is the canonical log.

**Last full benchmark snapshot**: `baselines/v3.7-final.json` — suite margin **+10.6** (variant 92.9 / bare 82.3), ship-gate FAIL because 5/8 gated fixtures ≥ +5 (need 7/9). Per-fixture detail in iteration 0001's "Actual change" section.

**Last subset benchmarks**:
- `baselines/v3.7-fix-f6f7.json` — F6 recovered −3 → +7 (validated), F7 invalidated by codex MCP race.
- `benchmark/auto-resolve/results/20260425T074946Z-09c8646-iter-0003-f7/` (not promoted to baselines) — F7 variant timed out cleanly under new watchdog (1201s, empty transcript, INVOKE_EXIT=124). Confirms (a) watchdog infra works, (b) MCP race is still the dominant F7 blocker. See iteration 0003 Lessons.

---

## What is shipped vs what is queued

### Shipped on this branch (iterations 0001, 0002, 0003)

| Commit | What it changed |
|---|---|
| `d11d81e` | `phase-1-build.md` — scope-first ordering + tests-as-contract bullets in quality_bar. `pipeline-routing.md` — `complexity: trivial → fast` + unrecognized-value fallback. |
| `b7e2a46` | `run-fixture.sh` variant prompt — removed forced "Run the full pipeline" phrase so `--engine auto` actually routes. Documentation note on phase-1-build.md tests-as-contract bullet (rule lands in EVAL, not BUILD). |
| `19cdf9b` | `run-fixture.sh` — `git remote add origin … && git symbolic-ref refs/remotes/origin/HEAD …` so native security-review resolves origin/HEAD instantly (eliminated the F8 56-min stall). |
| `f2ec62f` | `SKILL.md` DOCS Job 2 — narrowed to verbatim-named files only. `oracle-scope-tier-{a,b}.py` — auto-exempt fixture's own spec file (`docs/roadmap/phase-*/<fixture_id>.md`). |
| `695050a` | All 8 affected fixture specs — added "Lifecycle note" bullet to Constraints declaring DOCS frontmatter status flip is benchmark lifecycle, not scope creep. |
| (uncommitted as of 2026-04-25) | `run-fixture.sh` — process-group watchdog (`set -m` + `exec claude` + `kill -- -PGID`); deletes dead TIMEOUT_CMD detection. Pre-suite stub test verified PG reaping. Iteration 0003. |

### Queued (next hypotheses, ordered)

The README.md "Next hypotheses (ordered)" section is the live queue. As of handoff:

1. **Iteration 0005 — Inner `codex exec` hermeticization.** Pre-drafted in `iterations/0005-codex-inner-isolation.md`. Iter 0004 isolated the outer `claude -p` but the inner `codex exec` still loaded user codex config (which declares `[mcp_servers.pencil]`). Round 4 traced F7's actual hang to an inner `codex exec` BUILD that ran 10+ minutes producing zero bytes, plus a `tail -f` monitor on it. Fix: `--ignore-user-config --ignore-rules --ephemeral` added to every skill-issued `codex exec` (canonical in `_shared/codex-config.md`; inline in `auto-resolve/references/engine-routing.md`). Prediction: F7 variant completes within timeout, margin ≥ +5.
2. **5-Why operationalization in CLAUDE.md.** Codex round 2 conceded option (a) — expand Karpathy #1 "Think Before Coding" to incorporate why-chain procedure under user's "widely applied" usage pattern. One-paragraph CLAUDE.md edit.
3. **DOCS Job 2 wider verification.** Confirm narrowing holds when a fixture spec body uses ambiguous "update the docs" phrasing. Build the fixture (or modify F8) and re-run.
4. **Held-out fixture set.** Don't build until overfitting signal appears (3+ fixtures improving with no intuitive mechanism).
5. **Adversarial-ask layer.** Expand benchmark to test harness against vague/workaround-tempting asks. Long-term direction.

---

## What's open / known issues

- **F7 variant hang** (multi-layer): iter 0003 bounded with watchdog, iter 0004 isolated outer claude from user MCP, iter 0005 (current) extends isolation to inner `codex exec`. The "0-byte transcript" symptom was misleading — `claude -p` only flushes at end-of-session; the real diagnostic is per-arm `--debug-file` (added in iter 0004) plus `~/.claude/projects/<project>/<session>.jsonl` (Claude Code's project log) for tool-use timestamps and arguments.
- **Ship-gate**: still FAIL (5/8 gated fixtures ≥ +5, need 7/9). After iteration 0005 lands and F7 retries cleanly, expected to flip to PASS.
- **F2 −4 and F4 −6** in v3.7-final: not real regressions — F2 is judge-noise (variance ±3 per axis), F4 is variant 100/100 with bare's ceiling rising from GPT-5.5 (lifted bare 79 → 86). No action needed.

---

## Don't lose these decisions

These are the things a fresh session is likely to reconsider but shouldn't:

1. **CLAUDE.md stays clean of conditional rules.** 5-Why in CLAUDE.md is the user's call after they corrected my framing — it's `Karpathy #1` expansion, NOT a new top-level rule. Don't put method-level rules into doctrine.

2. **RUBRIC.md does not change** during a benchmarking window. Skill changes get measured against the existing rubric; comparability across iterations depends on this.

3. **Don't build held-out fixtures yet.** Pre-building anti-overfitting infra before observing overfitting reduces optimization surface for no reason. The signal to act is "3+ fixtures improve together with no intuitive mechanism".

4. **Don't blanket-kill `codex-mcp-server` processes.** Iteration 0003's narrow fix is a wall-clock timeout per `codex exec`. Reaping stale MCP servers is optional; if added, use the conservative whitelist pattern from `devlyn:reap`. Blanket-killing breaks other Claude Code plugins.

5. **The four oracles (test-fidelity, scope-tier-a, scope-tier-b, fixture spec annotations) are not the AutoResearch loop.** They are tools the loop uses. The loop is iteration files + DECISIONS.md + benchmarks. The oracles are infrastructure that earns its place when its findings drive a future iteration's decisions.

---

## How to start a new iteration in a fresh session

```bash
cd /Users/aipalm/Documents/GitHub/devlyn-cli
git checkout benchmark/v3.6-ab-20260423-191315  # or current working branch

# 1. Read the queue
cat autoresearch/README.md  # "Next hypotheses (ordered)" section

# 2. Read the most recent iteration as a worked example
ls autoresearch/iterations/ | tail -1 | xargs -I{} cat autoresearch/iterations/{}

# 3. Read PRINCIPLES.md
cat autoresearch/PRINCIPLES.md

# 4. Read the playbook
cat autoresearch/playbooks/iteration-loop.md

# 5. Pick the top hypothesis (or override with explicit rationale)
# 6. Create iterations/NNNN-<slug>.md from the schema in playbooks/
# 7. Cross-check the proposed change with codex 5.5 (per memory feedback_codex_cross_check.md)
# 8. Apply the change, run the benchmark, fill in Actual + Lessons + Decision
# 9. Update DECISIONS.md
# 10. Freeze baseline if shipped
```

---

## Memory entries that matter for this work

(stored in `~/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/memory/`)

- `feedback_codex_cross_check.md` — when and how to cross-check with codex 5.5 (dual-model GAN pattern). Non-trivial design decisions get a round. Iteration files document the round outcome.
- `feedback_auto_resolve_autonomy.md` — auto-resolve must be hands-free (no mid-pipeline prompts). Iterations changing skill prompts must preserve this.
- `project_v3_*.md` series — historical context on harness redesign. v3.5 is most recent shipped before this work; v3.7 is the current iteration target.

A new memory entry summarizing the AutoResearch framework itself should be written by the next session as part of onboarding (or by this session as the last act, if context permits).
