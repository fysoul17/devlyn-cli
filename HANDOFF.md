# HANDOFF — Lane B instruction-sensitivity benchmark, Day 2 continuation

**Read this first if you are picking up the Lane B benchmark work cold.**

Created: 2026-05-22. Owner: Terry K. Last completed step: Day 1 scaffold + commit + push to `origin/main`.

## What this is

A new measurement lane (`benchmark/instruction-sensitivity/`) that quantifies whether changes to `CLAUDE.md` / `AGENTS.md` / `runtime-principles.md` / skill SKILL.md bodies actually shift LLM behavior. Lane A (`benchmark/auto-resolve/`) measures pair-mode / risk-probe / headroom; Lane B fills the gap on the solo arm, which Lane A intentionally froze.

The complete design + rationale is already on disk — don't re-derive it. Read these in order:

1. `benchmark/README.md` — two-lane hub + decision rule + when to use which
2. `benchmark/instruction-sensitivity/README.md` — Lane B overview + I/O contract + status table
3. `benchmark/instruction-sensitivity/RUBRIC.md` — instruction-blind judge prompt + scoring contract
4. This file — what's done, what's next, what NOT to change

## Where Day 1 left off

Day 1 deliverables (committed and pushed):

| Component | State |
|---|---|
| `benchmark/README.md` (two-lane hub) | written |
| `benchmark/instruction-sensitivity/README.md` | written |
| `benchmark/instruction-sensitivity/RUBRIC.md` | written |
| Fixtures B1–B6 (`spec.md`, `task.txt`, `metadata.json`, `scope-allowlist.txt`, `behavior-contract.json`) | written |
| `scripts/detect-mechanical.py` v0 | working — 4 of 8 signals (`off_scope_file_touches`, `off_scope_line_delta`, `hedge_bloat_phrases`, `preexisting_deadcode_touched`) |
| `scripts/run-compare.sh` | skeleton — writes `manifest.json` + arm dir layout |
| `scripts/run-fixture.sh` | skeleton — prints prompt + expected output paths |
| `scripts/judge-blind.sh` | skeleton — input validation + Day 2 wiring spec |
| `scripts/score-behavior.py` | skeleton — `aggregate()` returns `verdict: SCAFFOLD` until judge wiring lands |

What's NOT yet on disk:
- `starter/` and `hidden/` directories inside each fixture are empty placeholders. Day 2 will populate them.
- No actual LLM driver wiring (`claude-code` / `codex` CLI integration into `run-compare.sh`).
- No `npx devlyn-cli benchmark instruction` subcommand in `bin/devlyn.js`.
- No real baseline-vs-candidate measurement has been run.

## Day 2 plan (this session's work)

Goal: **first real `solo_old` vs `solo_new` measurement of the behavioral patch already on disk** (the two Karpathy-gap edits committed at the same time as the Lane B scaffold — see Karpathy gap commit). Concretely:

1. **Populate fixture `starter/` directories.** Each B1–B6 needs a tiny initial repo state — the actual `src/format-user.js`, `src/pricing.js`, etc. that the agent will edit. Keep them MINIMAL — single file, 5–20 lines. The fixture's trap is in the spec ambiguity / bait surface, not in code volume.

2. **Populate fixture `hidden/verify.sh` + `hidden/detector-config.json`.** Hidden from the agent and judge. The verify script asserts the mechanical signals defined in `behavior-contract.json` `bad_signals` did not fire.

3. **Wire a driver into `run-compare.sh` + `run-fixture.sh`.** Recommended: use `claude` CLI (already on the system) in print mode against a worktree at the pinned ref. The driver must:
   - Check out the ref into a temp worktree
   - Cd into a copy of the fixture's `starter/`
   - Feed `task.txt` to the driver
   - Capture stdout/stderr → `transcript.txt`
   - `git diff` → `diff.patch`
   - Record wall-time + exit status → `meta.json`

4. **Wire the judge call into `judge-blind.sh`.** Use the Codex CLI helper (`mcp__codex-cli__codex`) so the judge model differs from the model under test. Send the rubric body in `RUBRIC.md` with the slot-randomized A/B fields. Output: strict JSON appended to `judge-findings.jsonl`.

5. **Complete `score-behavior.py` aggregation.** The skeleton already defines the 7-axis schema and IMPROVED / REGRESSED / MIXED rule — implement the actual tally.

6. **Run the first measurement.** Baseline = the commit JUST BEFORE the Karpathy-gap commit (probably `f354974` or whatever HEAD was when this session started — check `git log --oneline` for the boundary). Candidate = the Karpathy-gap commit. Expected directional outcome: `clarification` and `orthogonal_edit_control` axes should trend `+1` if the patch works. NO improvement on `pushback` is fine — we did not add explicit pushback rules.

7. **Sample human audit (15 items).** Pick 5 from `detector-findings.jsonl` + 10 from `judge-findings.jsonl`. Log disagreements to `judge-calibration.jsonl` for Day 3.

Time budget: Day 2 was estimated at ~3–6 hours runtime + driver-wiring dev time. Use Codex pair-collaboration on the driver design before writing it.

## What NOT to touch (load-bearing constraints)

These are decisions the user has already locked in. Re-litigating them wastes the session:

- **Lane A (`benchmark/auto-resolve/`)** stays frozen — do not extend it for instruction measurement. The two lanes are intentionally separated to avoid mixed signals.
- **CLAUDE.md ↔ AGENTS.md drift is intentional.** The user explicitly said Claude and Codex consume them differently. Do NOT sync the two files just because they diverge on small things. (Behavior rules ARE synced — Karpathy clarification + surgical rules are in both files.)
- **CLAUDE.md ↔ runtime-principles.md marker parity (lint Check 12)** is enforced. If you change `subtractive-first`, `goal-locked`, or `evidence` blocks in CLAUDE.md, mirror to `config/skills/_shared/runtime-principles.md` AND copy to `.claude/skills/_shared/` AND `.agents/skills/_shared/`. `no-workaround` was removed from the mirror set in this session — do not re-add it.
- **`agents-config/evaluator.md`** is dormant but retained as reference for a future grading sub-agent. The user chose preservation over deletion. The installer is now decoupled (`bin/devlyn.js` installs skills regardless of agents-config presence), so the dormant file does not break anything.
- **Saint-Exupéry quote** appears exactly once now (in the discipline rule). The subtractive-first block references it by name only. Do not re-add the literal quote into the marker block — Check 12 will pass either way, but it dilutes the original intent.
- **Subtractive / Goal-locked body compression** was explicitly DEFERRED by the user — the "safety text" effect on LLM behavior was deemed worth keeping. Do not propose ~30% body cuts again unless the user reopens it.
- **`README.md:182, 186`** has retired-surface references that fail lint Check 10c. This is a FALSE POSITIVE on a deliberate migration table. Leave it alone unless the user asks otherwise.
- **`rg: command not found`** on this dev machine — some lint checks silently skip. Not in scope to fix.

## Decision log from this session (so you don't have to re-derive)

Both Codex collaboration rounds reached convergent conclusions. Highlights worth keeping:

1. **Lane B is needed because Lane A's solo arm is frozen.** Karpathy notes (Dec 2025) say models still ignore "instructions in CLAUDE.md" attempts — so we need a measurement loop dedicated to whether instruction edits actually shift behavior.
2. **Mechanical detector runs first, judge second.** Cheap deterministic signals tie-break the judge when the judge is uncertain. Order matters for cost and for bias control.
3. **Instruction-blind judge is non-negotiable.** Judge prompt MUST exclude: arm identity, commit SHAs, CLAUDE.md text itself. A/B slots randomized per fixture. Cross-model judge (judge model ≠ model under test).
4. **Output is 7-axis behavior score, NOT pass/fail.** `summary_verdict ∈ {IMPROVED, MIXED, REGRESSED}` — derived, not primary. PASS/FAIL on behavior axes is reductive.
5. **change-neutral vs change-behavioral split** is the gating rule. Lint-passable rewordings of the same meaning do NOT need a Lane B run. Karpathy-gap-class additions DO.
6. **Codex's 3-day plan is more realistic than 1.5-day.** Day 1 (done) = scaffold. Day 2 (this session) = driver + first measurement. Day 3 = human audit + CLI integration.

## Quick commands for cold-start

```bash
# Sanity — confirm everything from Day 1 is present
ls benchmark/instruction-sensitivity/fixtures/B*/spec.md | wc -l   # must be 6
python3 benchmark/instruction-sensitivity/scripts/detect-mechanical.py --help
python3 benchmark/instruction-sensitivity/scripts/score-behavior.py --help
bash benchmark/instruction-sensitivity/scripts/run-compare.sh 2>&1 | head -1  # prints usage

# Lint (Check 12 must pass; README:186 may still fail — that's known)
bash scripts/lint-skills.sh 2>&1 | grep -E '✗|Check 12'

# Find the baseline commit (the one right before the Karpathy-gap edits)
git log --oneline -20

# First Day 2 step — pair with Codex on driver design
# (Use the codex MCP tool with collaboration mode, reference this HANDOFF +
#  benchmark/instruction-sensitivity/README.md as context)
```

## Known issues to surface, not solve

- **pyx-memory `service_unavailable`**: every store attempt during Day 1 returned `Memory instance failed to provision. Delete and recreate the instance.` The user has been told. Do not retry blindly in Day 2 — assume the same failure until the user signals the instance is back. Use this HANDOFF + commit messages as the persistence layer instead.
- **AGENTS.md `109-175` is installer output, not source.** Do not hand-edit. The real source is `agents-config/evaluator.md`; the installer rewrites the AGENTS.md tail on every run.
- **`worktree-agent-*` branches in `git branch -vv`** are agent worktrees from earlier sessions. They are not part of Day 2 — ignore unless explicitly cleaning up.

## When Day 2 is done

Update this HANDOFF in-place with what changed (next session's cold-start needs the same quality of context handover you got). Mark each Day 2 step ✓ or note why it slipped. Then commit + push and the user will pick up Day 3.
