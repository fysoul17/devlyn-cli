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
│   ├── ship-gate.py          # applies thresholds + writes history record
│   ├── run-headroom-candidate.sh
│   ├── headroom-gate.py      # blocks pair measurement without headroom set
│   ├── test-headroom-gate.sh
│   ├── run-full-pipeline-pair-candidate.sh
│   ├── full-pipeline-pair-gate.py
│   ├── test-full-pipeline-pair-gate.sh
│   ├── run-frozen-verify-pair.sh
│   ├── fetch-swebench-instances.py
│   ├── collect-swebench-predictions.py
│   ├── run-swebench-solver-batch.sh
│   ├── prepare-swebench-frozen-case.py
│   ├── prepare-swebench-frozen-corpus.py
│   ├── run-swebench-frozen-corpus.sh
│   ├── swebench-frozen-matrix.py
│   ├── test-swebench-frozen-case.sh
│   ├── frozen-verify-gate.py # gates frozen VERIFY pair-lift evidence
│   └── test-frozen-verify-gate.sh
│
├── external/swebench/        # ignored local imports of SWE-bench cases/repos
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
7. Run `bash scripts/lint-fixtures.sh`.

For L2/pair candidate fixtures, also run:

```bash
bash benchmark/auto-resolve/scripts/run-headroom-candidate.sh F16-cli-quote-tax-rules
```

This runs only the arms needed for calibration (`bare` and `solo_claude`),
blind-judges them, and applies `headroom-gate.py`. A candidate set is not
usable for pair measurement unless at least two fixtures pass and each fixture
has clean `bare <= 60` and `solo_claude <= 80` scores. A one-fixture calibration
run can show useful scores but does not satisfy the set gate.
When changing the gate itself, run:

```bash
bash benchmark/auto-resolve/scripts/test-headroom-gate.sh
```

After a full-pipeline pair run has the calibrated arms (`bare`,
`solo_claude`, `l2_gated` or `l2_risk_probes`) plus a blind `judge.json`, gate
it separately:

```bash
bash benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  --max-pair-solo-wall-ratio 3 \
  F21-cli-scheduler-priority F23-cli-fulfillment-wave
```

The runner executes `bare` + `solo_claude`, applies `headroom-gate.py`, and
only then spends a `l2_gated` arm. To gate already-existing artifacts:

When a prompt-only pair change needs a fresh `l2_gated` measurement but the
calibrated `bare` + `solo_claude` arms are already clean, reuse them into a new
run id:

```bash
bash benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  --run-id <new-run-id> \
  --reuse-calibrated-from <prior-headroom-run-id> \
  --max-pair-solo-wall-ratio 3 \
  F21-cli-scheduler-priority F23-cli-fulfillment-wave
```

```bash
python3 benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  --run-id <full-pipeline-run-id> \
  --min-fixtures 2 \
  --min-pair-margin 5 \
  --max-pair-solo-wall-ratio 3 \
  --out-json benchmark/auto-resolve/results/<full-pipeline-run-id>/full-pipeline-pair-gate.json \
  --out-md benchmark/auto-resolve/results/<full-pipeline-run-id>/full-pipeline-pair-gate.md
```

This is the full-pipeline claim gate: each counted fixture must satisfy the
headroom precondition (`bare <= 60`, `solo_claude <= 80`), the selected pair arm
must be clean, `pair_mode` must be true in the captured resolve state, and the
blind judge must score the pair arm at least `--min-pair-margin` above
`solo_claude`. `l2_risk_probes` is the current measured pair arm for the
F16/F25 gate: `20260509-f16-f25-combined-cartprobe-v2` passed with margins +21
and +24, average pair/solo wall ratio 1.46x. When changing this gate, run:

```bash
bash benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh
```

Commands that reference `BENCH_FIXTURE_DIR` are hidden post-run oracles: they
are not staged into BUILD_GATE's `.devlyn/spec-verify.json`.

To compare pair VERIFY against solo VERIFY on a frozen implementation diff,
run:

```bash
bash benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  --fixture F16-cli-quote-tax-rules \
  --diff benchmark/auto-resolve/results/<run-id>/F16-cli-quote-tax-rules/solo_claude/diff.patch \
  --pair-mode gated
```

This applies the diff before `/devlyn:resolve` starts, then runs verify-only
solo and pair arms against the same committed work tree. `--pair-mode gated`
tests the product trigger policy; `--pair-mode forced` adds `--pair-verify` for
diagnostics. Use non-empty diffs only; empty diffs fail fast because they are
not valid pair evidence.
Hidden verifier context is available during VERIFY, so this runner prevents
IMPLEMENT contamination but is not an oracle-blind judge setup.
The runner writes `compare.json`; `pair_verdict_lift: true` means pair VERIFY
actually ran and found a verdict-binding issue that solo VERIFY did not.
If an imported case has no deterministic `verification_commands`, the runner
does not create `.devlyn/spec-verify.json`; an empty carrier is malformed by the
normal real-user contract and must not block qualitative frozen review.

To gate a set of frozen VERIFY results mechanically:

```bash
python3 benchmark/auto-resolve/scripts/frozen-verify-gate.py \
  --run-id 20260505T173913Z-9986cd3-frozen-verify \
  --run-id 20260505T230215Z-9986cd3-frozen-verify \
  --max-pair-solo-wall-ratio 3 \
  --out-json benchmark/auto-resolve/results/frozen-verify-gate-20260505.json \
  --out-md benchmark/auto-resolve/results/frozen-verify-gate-20260505.md
```

When changing the gate itself, run its regression test:

```bash
bash benchmark/auto-resolve/scripts/test-frozen-verify-gate.sh
```

This is deliberately narrower than `headroom-gate.py`: it does not claim
full-pipeline pair superiority. It proves only that, after the implementation
diff is frozen, gated pair VERIFY fires and returns a stricter verdict-binding
result than solo VERIFY on the same diff. Each supplied run must cover a
distinct fixture; repeated runs of the same fixture do not count as independent
corpus growth. `--max-pair-solo-wall-ratio` is optional, but use it for
ship-style evidence so quality lift is not accepted without a reasonable
wall-time bound. The gate infers the fixture id from the runner input metadata;
artifacts without that metadata, or with a fixture id absent from
the selected `--fixtures-root`, fail instead of being counted as anonymous or
fake evidence.

### SWE-bench fixed-diff review pilot

SWE-bench is useful here as an external, widely known corpus, but the first
measurement surface should remain frozen VERIFY rather than full-pipeline
generation. The official dataset fields include `instance_id`, `repo`,
`base_commit`, `problem_statement`, `patch`, and `test_patch`; SWE-bench Lite is
the smaller subset and SWE-bench Verified is the human-validated subset.
See:

- https://www.swebench.com/SWE-bench/guides/datasets/
- https://www.swebench.com/lite.html
- https://www.swebench.com/verified.html

Fetch a small official Lite/Verified instance file without installing the
Hugging Face Python stack:

```bash
python3 benchmark/auto-resolve/scripts/fetch-swebench-instances.py \
  --dataset lite \
  --limit 5 \
  --out benchmark/auto-resolve/external/swebench/instances-lite.jsonl
```

Prepare one case from an instance JSON and a candidate patch produced by a solo
run or another external solver:

```bash
python3 benchmark/auto-resolve/scripts/prepare-swebench-frozen-case.py \
  --instance-json /path/to/swebench-instance.json \
  --model-patch /path/to/solo-candidate.patch
```

Or prepare a small corpus from the official SWE-bench prediction JSONL shape
(`instance_id`, `model_name_or_path`, `model_patch`):

```bash
python3 benchmark/auto-resolve/scripts/collect-swebench-predictions.py \
  --patch-root /path/to/logs \
  --instances-jsonl benchmark/auto-resolve/external/swebench/instances-lite.jsonl \
  --model-name external-solo \
  --out benchmark/auto-resolve/external/swebench/solo-predictions.jsonl
```

The collector expects `/path/to/logs/<instance_id>/patch.diff`; it is useful
when another solver or a downloaded SWE-bench log bundle provides per-instance
patch files rather than prediction JSONL.

```bash
python3 benchmark/auto-resolve/scripts/prepare-swebench-frozen-corpus.py \
  --instances-jsonl benchmark/auto-resolve/external/swebench/instances-lite.jsonl \
  --predictions-jsonl /path/to/solo-predictions.jsonl \
  --limit 5 \
  --out-manifest benchmark/auto-resolve/external/swebench/manifest.json
```

Then run the command written to
`benchmark/auto-resolve/external/swebench/cases/<instance_id>/run-command.txt`.
For a one-off case, the command uses:

```bash
bash benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  --fixture <instance_id> \
  --fixtures-root benchmark/auto-resolve/external/swebench/cases \
  --base-repo benchmark/auto-resolve/external/swebench/repos/<repo-cache> \
  --diff benchmark/auto-resolve/external/swebench/cases/<instance_id>/model.patch \
  --pair-mode gated
```

For a prepared corpus manifest, run the whole set and gate it:

```bash
bash benchmark/auto-resolve/scripts/run-swebench-frozen-corpus.sh \
  --manifest benchmark/auto-resolve/external/swebench/manifest.json \
  --min-runs 2 \
  --max-pair-solo-wall-ratio 3 \
  --timeout-seconds 900 \
  --resume-completed-arms \
  --run-ids-out benchmark/auto-resolve/results/swebench-frozen-run-ids.txt \
  --out-json benchmark/auto-resolve/results/swebench-frozen-gate.json \
  --out-md benchmark/auto-resolve/results/swebench-frozen-gate.md
```

To re-gate existing run ids without re-invoking providers, write one run id per
line and pass `--gate-only-run-ids <file>` with the same manifest. For large
tranches, keep `--run-ids-out` and use `--resume-completed-arms` on retries:
successful solo/pair arms are reused, while failed or provider-limited arms run
again. The run ids file is the durable handle for gate-only reruns and matrix
rendering after a bounded run finishes.

To produce local candidate patches for a bounded pilot, prepare a solver
worktree from the same instance JSONL. The generated spec contains only the
visible SWE-bench problem statement; do not read the instance's gold `patch` or
`test_patch` while solving.

```bash
python3 benchmark/auto-resolve/scripts/prepare-swebench-solver-worktree.py \
  --instances-jsonl benchmark/auto-resolve/external/swebench/instances-lite.jsonl \
  --instance-id django__django-11019 \
  --copy-devlyn-context
```

Run the prompt in `<worktree>/solve-prompt.txt`, save the resulting diff as
`<patch-root>/<instance_id>/patch.diff`, then use
`collect-swebench-predictions.py` to create prediction JSONL.

For a bounded local pilot, the batch runner performs those steps
sequentially and collects prediction JSONL. It redirects provider stdin away
from the manifest stream so later rows cannot be consumed by a child process.
The generated solver worktrees and repo caches can become large; once
`predictions-out` is written and cases are prepared, remove ignored local cache
directories such as `external/swebench/worktrees/` and
`external/swebench/repos-solver/` if disk pressure would otherwise interrupt
the frozen corpus run. Use `--timeout-seconds` and `--resume` for large
tranches; long-tail solver rows should be recorded as throughput failures
instead of letting one row hold the whole suite open.

```bash
bash benchmark/auto-resolve/scripts/run-swebench-solver-batch.sh \
  --instances-jsonl benchmark/auto-resolve/external/swebench/instances-lite.jsonl \
  --instance-id django__django-11039 \
  --instance-id django__django-11049 \
  --predictions-out benchmark/auto-resolve/external/swebench/predictions-lite.jsonl \
  --copy-devlyn-context
```

Gate a SWE-bench review pilot by pointing the existing frozen gate at the
external case root:

```bash
python3 benchmark/auto-resolve/scripts/frozen-verify-gate.py \
  --fixtures-root benchmark/auto-resolve/external/swebench/cases \
  --run-id <swebench-frozen-run-1> \
  --run-id <swebench-frozen-run-2> \
  --run-id <swebench-frozen-run-3> \
  --min-runs 3 \
  --max-pair-solo-wall-ratio 3 \
  --out-json benchmark/auto-resolve/results/swebench-frozen-gate.json \
  --out-md benchmark/auto-resolve/results/swebench-frozen-gate.md
```

This gives evidence for "pair review catches solo-missed verdict-binding issues
on real SWE-bench patches." The gate accepts either external solo-vs-pair
verdict lift or internal pair lift (`pair_judge` stricter than the pair run's
primary judge), because separate solo and pair primary judges are stochastic.
For evidence intended to support shipping policy, also set a wall-ratio cap and
inspect `avg_pair_solo_wall_ratio` plus each row's `pair_solo_wall_ratio`.
For selection-bias control, render every run in the attempted pilot, not just
gate rows. The matrix reports verdict-lift rows separately from recall-only
rows where pair found additional findings but did not change the binding
verdict. It also reports classification counts, gate rate, and trailing
non-gate rows. Use the optional yield thresholds when the matrix is meant to
fail closed instead of only documenting that additional rows are adding
controls without strengthening the proof gate:

```bash
python3 benchmark/auto-resolve/scripts/swebench-frozen-matrix.py \
  --title "SWE-bench Lite Frozen VERIFY Matrix" \
  --verdict MIXED_WITH_GATE_PASS \
  --gate-json benchmark/auto-resolve/results/swebench-frozen-gate.json \
  --run-id <swebench-frozen-run-1> \
  --run-id <swebench-frozen-run-2> \
  --min-gate-rate 0.25 \
  --max-trailing-non-gate 10 \
  --out-json benchmark/auto-resolve/results/swebench-frozen-matrix.json \
  --out-md benchmark/auto-resolve/results/swebench-frozen-matrix.md
```

It does not measure official SWE-bench solve rate; run the official SWE-bench
evaluator separately for that metric. When changing the importer or
external-base runner path, run:

```bash
bash benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh
```

Do not use the retired full-pipeline `l2_forced` arm as pair evidence. It puts
`--pair-verify` in the initial prompt, so IMPLEMENT can become pair-aware before
the diff is frozen.

## LLM-upgrade resilience

- **No model hardcoding.** Judge runs `codex exec` without `-m`, inheriting whichever flagship the CLI currently ships. Each run captures `_judge_model` for historical provenance.
- **Margin-based gates.** Ship thresholds use margin (variant − bare), not absolute score. Both arms improve together as models improve; the harness-added value measured by margin stays meaningful.
- **Saturation rotation.** When both arms exceed 95 on a fixture for two shipped versions, rotate it (see `RUBRIC.md::Fixture Rotation Policy`).

## Ship gates (summary — see `RUBRIC.md` for full spec)

Hard floors (any one fails → block):

- Zero variant disqualifier (silent catch, fabricated verification, extra deps beyond `max_deps_added`, etc.).
- `F9-e2e-ideate-to-resolve` must PASS (novice-flow contract).
- ≥ 7 of 9 gated fixtures have margin ≥ +5.
- No per-fixture regression worse than −5 vs last shipped baseline.

Soft gates (warning, not block): suite-margin drop > 3, fixture losing its margin, critical-finding catch-rate regression vs last shipped variant.

## Running the full suite (real)

Full real benchmarks usually take 2-3 minutes per arm for simple fixtures and
up to 15 minutes per arm for strict-route fixtures. A full n=1 run of 9 fixtures
× 2 arms can take 30 min - 2 hrs depending on routes taken.

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
