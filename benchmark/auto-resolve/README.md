# devlyn-cli auto-resolve Benchmark Suite

One-command A/B benchmark that gates every harness change with a ship/rollback decision.

## Quick start

```bash
npx devlyn-cli benchmark                 # n=1 smoke, all fixtures × 2 arms, judge, report, ship-gate
npx devlyn-cli benchmark --n 3           # higher confidence for ship decisions
npx devlyn-cli benchmark F2              # specific fixture only
npx devlyn-cli benchmark --dry-run       # validate suite wiring without model invocation
npx devlyn-cli benchmark --bless         # if ship-gate PASSes, promote this run as the shipped baseline
npx devlyn-cli benchmark --judge-only --run-id <ID>   # re-judge an existing run's artifacts
```

Exit code 0 = PASS, 1 = FAIL.

## What it does

1. For every fixture × arm (`variant` / `bare`):
   - Prepare a fresh temp copy of `fixtures/test-repo/`.
   - Commit baseline + apply `setup.sh` + commit bench scaffolding.
   - Invoke the arm via an isolated `claude -p` subprocess.
   - Capture `diff.patch`, `transcript.txt`, `timing.json`, run `expected.json::verification_commands`.
2. For every fixture, invoke `codex exec` as a blind judge (`A`/`B` randomized per fixture) using the 4-axis rubric in `RUBRIC.md`.
3. Aggregate into `results/<run-id>/report.md` + `summary.json`.
4. Apply ship-gate thresholds (`scripts/ship-gate.py`). Print verdict.
5. Append immutable record to `history/runs/<run-id>.json`.

## Directory layout

```
benchmark/auto-resolve/
├── BENCHMARK-DESIGN.md       # full design rationale
├── README.md                 # this file
├── RUBRIC.md                 # 4-axis scoring + ship gates
│
├── fixtures/
│   ├── SCHEMA.md             # fixture file format
│   ├── test-repo/            # bootstrap Node project — base for all arms
│   ├── F2-cli-medium-subcommand/
│   └── F1,F3-F9/             # add per Stage 2-3
│
├── scripts/
│   ├── run-suite.sh          # single entry — called by `npx devlyn-cli benchmark`
│   ├── run-fixture.sh        # one fixture × one arm, self-contained
│   ├── judge.sh              # Codex blind judge for one fixture
│   ├── compile-report.py     # aggregates into report.md + summary.json
│   └── ship-gate.py          # applies thresholds + writes history record
│
├── results/<run-id>/         # per-run artifacts (overwritten)
└── history/
    ├── runs/                 # append-only, one JSON per run
    ├── latest.json           # pointer to most recent run
    └── baselines/shipped.json   # last blessed version, used for regression floor
```

## Prerequisites

- `claude` CLI on PATH (Claude Code, used to invoke each arm).
- `codex` CLI on PATH (used by the blind judge). Install from https://platform.openai.com/docs/codex.
- `python3`, `node`, `git`, `timeout`.

## Adding a fixture

Follow `fixtures/SCHEMA.md`. Six files per fixture: `metadata.json`, `spec.md`, `task.txt`, `expected.json`, `NOTES.md`, `setup.sh`. Common workflow:

1. Copy an existing fixture directory as a template.
2. Rewrite `metadata.json::intent` with the new task's plain-language intent.
3. Write `spec.md` (auto-resolve-ready) and `task.txt` (plain prompt) both derived from the intent.
4. Fill `expected.json` with concrete verification commands and forbidden patterns.
5. Document purpose + failure mode in `NOTES.md`.
6. Add `setup.sh` if the task needs the base `test-repo` modified before either arm starts.

## LLM-upgrade resilience

- **No model hardcoding.** Judge runs `codex exec` without `-m`, inheriting whichever flagship the CLI currently ships. Each run captures `_judge_model` for historical provenance.
- **Margin-based gates.** Ship thresholds use margin (variant − bare), not absolute score. Both arms improve together as models improve; the harness-added value measured by margin stays meaningful.
- **Saturation rotation.** When both arms exceed 95 on a fixture for two shipped versions, rotate it (see `RUBRIC.md::Fixture Rotation Policy`).

## Ship gates (summary — see `RUBRIC.md` for full spec)

Hard floors (any one fails → block):

- Zero variant disqualifier (silent catch, fabricated verification, extra deps beyond `max_deps_added`, etc.).
- `F9-e2e-ideate-to-preflight` must PASS (novice-flow contract).
- ≥ 7 of 9 gated fixtures have margin ≥ +5.
- No per-fixture regression worse than −5 vs last shipped baseline.

Soft gates (warning, not block): suite-margin drop > 3, fixture losing its margin, critical-finding catch-rate regression vs last shipped variant.

## Running the full suite (real)

Full real benchmark costs roughly 2-3 minutes per arm for simple fixtures and up to 15 minutes per arm for strict-route fixtures. A full n=1 run of 9 fixtures × 2 arms can take 30 min – 2 hrs depending on routes taken.

```bash
# Smoke run before ship decisions
npx devlyn-cli benchmark

# Ship-decision run
npx devlyn-cli benchmark --n 3 --label v3.7 --bless
```

## Dry-run

`--dry-run` skips model invocation. It still:

- Prepares each fresh work dir.
- Writes arm-specific prompts.
- Commits the baseline.
- Applies `setup.sh`.
- Runs verification commands (which will mostly fail since no implementation was added).

Use it to sanity-check new fixtures or runner changes before burning model tokens.
