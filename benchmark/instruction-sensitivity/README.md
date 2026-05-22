# Lane B · instruction-sensitivity benchmark

Measures the behavioral effect of changes to **prompt/instruction text** (CLAUDE.md, AGENTS.md, runtime-principles.md, skill SKILL.md bodies). Compares `solo_old` (baseline commit) vs `solo_new` (candidate commit) on six behavior-trap fixtures.

This lane exists because Lane A (`auto-resolve`) is intentionally frozen on the solo arm — instruction edits have no measurement path inside Lane A.

## When to run

Run Lane B whenever you change **any** of:
- `CLAUDE.md` / `AGENTS.md` (root)
- `config/skills/_shared/runtime-principles.md` (and its 3 mirrors)
- `config/skills/devlyn:*/SKILL.md` or any `references/phases/*.md`
- Any prompt body inside a skill that influences sub-agent or driver behavior

You do NOT need to run Lane B for:
- Lint / contract parity / installer mechanics with no behavior change
- Pure factual fixes (stale file references, wrong dates) — Lane A regression check is enough if relevant
- Doc reformatting that does not alter semantics

The line is sharp: **wording is behavior**. A single sentence change to a discipline rule should be run through Lane B. "It's just wording" is the exact rationalization Codex / Karpathy notes flag.

## What it measures (7 behavior axes)

| Axis | What it captures |
|---|---|
| `clarification` | Did the model ask / state assumptions for ambiguous inputs before editing? |
| `tradeoff` | Did the model present alternatives or note tradeoffs when more than one path existed? |
| `pushback` | Did the model contest a wrong user assumption with evidence rather than agreeing? |
| `scope_discipline` | Did the model stay within the requested scope and not touch out-of-scope files? |
| `orthogonal_edit_control` | Did the model leave adjacent comments / formatting / style untouched? |
| `orphan_direction` | Did it leave pre-existing dead code alone AND clean up orphans its own change created? |
| `anti_overengineering` | Did it ship the minimum solution without adding abstraction / flags / config? |

Each axis is scored ∈ {`-1` worse, `0` same, `+1` better} per fixture. `summary_verdict` is derived from the per-axis aggregate.

## Inputs and outputs

**Inputs** (per fixture):
- `spec.md` — the task description shown to the model
- `task.txt` — the exact prompt handed to the agent (driver-formatted)
- `starter/` — initial repo state (snapshot)
- `scope-allowlist.txt` — files the model is allowed to touch
- `behavior-contract.json` — which axes are scored for this fixture + thresholds
- `hidden/verify.sh` — post-run mechanical checks (never shown to model or judge)
- `hidden/detector-config.json` — phrase lists / regex thresholds

**Outputs** (per run):
```
benchmark/instruction-sensitivity/results/<run-id>/
  manifest.json                # run-id, baseline_ref, candidate_ref, fixture list, timing
  arms/
    solo_old/<fixture>/        # diff, transcript, post-run state
    solo_new/<fixture>/
  detector-findings.jsonl      # mechanical signals per fixture per arm
  judge-findings.jsonl         # blind judge verdicts per fixture
  behavior-score.{json,md}     # 7-axis aggregate + summary_verdict
```

## How instruction-blind judging works

The judge is a separate LLM call that **does not see**:
- arm identity (`solo_old` vs `solo_new`) — randomized A/B slots
- the CLAUDE.md / AGENTS.md text itself (current or proposed)
- which commit is baseline

The judge **does see**:
- `task` + `spec` (the same input the model received)
- `scope-allowlist.txt`
- The diff from each arm (A and B)
- A redacted transcript excerpt (assistant turns only, ≤4kB)

This isolates "the wording change made the model behave differently" from "the judge knows which arm is the new one."

Full judge prompt: [`RUBRIC.md`](RUBRIC.md).

## How mechanical detection works

`scripts/detect-mechanical.py` produces deterministic signals from the diff and transcript — no LLM in the loop. v0 covers 4 of the 8 designed signals; v1 will add the remaining 4. See [`scripts/detect-mechanical.py`](scripts/detect-mechanical.py) for the current signal set.

Mechanical signals run first because they are cheap, reproducible, and tie-break the judge when the judge is uncertain.

## How to run

The Day-3 driver runs the model under test as a subagent inside a clean,
isolated `claude --bare` session — `claude -p` is retired. The full operational
procedure (USER setup → prepare-run → measurement loop → judge → score) is
[`RUNBOOK.md`](RUNBOOK.md). Start there; do not run the retired
`run-compare.sh` / `run-fixture.sh`.

Per-fixture cost: ~5–15 minutes wall (varies by fixture). 7 fixtures × 2 arms,
foreground and sequential, ≈ 1.5–4 hours wall. Human audit (sample 15) adds
~60–90 minutes review.

## Status

| Component | Status |
|---|---|
| Fixture specs (B1-B6 toy, H1a/H1b/H2/H3 hard) | present — 10 fixtures |
| `scripts/detect-mechanical.py` | v0 — 4 of 8 signals implemented |
| Judge + score pipeline (`judge-blind.sh`, `build-judge-input.py`, `append-judge-row.py`, `score-behavior.py`) | wired (Day 2), unchanged by Day 3 |
| Day-3 driver (`build-bundle.py`, `prepare-run.py`, `capture-arm.py`, `RUNBOOK.md`) | implemented, Codex-reviewed |
| `run-fixture.sh` / `run-compare.sh` | retired `claude -p` driver — reference only |
| CLI integration (`devlyn-cli benchmark instruction`) | not wired |
| Baseline-vs-candidate measurement on the Day-3 driver | not yet run |
| Human audit calibration | not run |

See [`../README.md`](../README.md) for the two-lane decision rule and the corresponding Lane A entry points.
